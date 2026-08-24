suppressPackageStartupMessages(library(mirt))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 8) {
  stop("usage: Rscript phase5_run_mv14_measurement_uncertainty_bootstrap.R <input_csv> <mv10_roles_csv> <out_dir> <seed> <smoke_R> <core_R> <dif_R> <collect_itemfit>")
}

input_csv <- args[[1]]
roles_csv <- args[[2]]
out_dir <- args[[3]]
seed <- as.integer(args[[4]])
smoke_R <- as.integer(args[[5]])
core_R <- as.integer(args[[6]])
dif_R <- as.integer(args[[7]])
collect_itemfit <- tolower(args[[8]]) %in% c("1", "true", "yes", "y")

if (is.na(seed) || is.na(smoke_R) || is.na(core_R) || is.na(dif_R)) {
  stop("seed, smoke_R, core_R, and dif_R must be integers")
}
if (smoke_R < 0 || core_R < 0 || dif_R < 0) {
  stop("bootstrap R counts must be non-negative")
}

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
set.seed(seed)

items <- sprintf("C%02d", 1:8)
item_labels <- c(
  C01 = "depressed_mood",
  C02 = "anhedonia",
  C03 = "sleep",
  C04 = "fatigue",
  C05 = "appetite",
  C06 = "self_worth",
  C07 = "concentration",
  C08 = "psychomotor"
)
lrt_alpha <- 0.01
bic_improvement_tol <- 2.0
core_ids <- c("configural", "metric", "scalar", "partial_mv10")
stable_ladder_ids <- c("metric", "partial_mv10", "scalar")

responses <- read.csv(input_csv, stringsAsFactors = FALSE, check.names = FALSE)
roles <- read.csv(roles_csv, stringsAsFactors = FALSE)

missing_items <- setdiff(items, names(responses))
if (length(missing_items) > 0) {
  stop(paste("missing item columns:", paste(missing_items, collapse = ",")))
}
if (!("dataset" %in% names(responses))) {
  stop("missing dataset column")
}

responses$dataset <- factor(responses$dataset, levels = c("edaic", "cmdc"))
if (any(is.na(responses$dataset))) {
  stop("dataset column must contain only edaic/cmdc")
}
responses[, items] <- lapply(responses[, items], function(col) as.integer(col))

role_for <- function(item) {
  row <- roles[roles$construct_id == item, , drop = FALSE]
  if (nrow(row) != 1) {
    stop(paste("missing MV10 role for", item))
  }
  row$partial_invariance_role[[1]]
}

constraint_terms <- function(slope_items = character(), threshold_items = character()) {
  terms <- character()
  for (item in slope_items) {
    idx <- match(item, items)
    terms <- c(terms, sprintf("(%d, a1)", idx))
  }
  for (item in threshold_items) {
    idx <- match(item, items)
    terms <- c(
      terms,
      sprintf("(%d, d1)", idx),
      sprintf("(%d, d2)", idx),
      sprintf("(%d, d3)", idx)
    )
  }
  terms
}

model_syntax <- function(slope_items = character(), threshold_items = character()) {
  terms <- constraint_terms(slope_items, threshold_items)
  if (length(terms) == 0) {
    return("F = 1-8")
  }
  paste("F = 1-8", paste("CONSTRAINB =", paste(terms, collapse = ", ")), sep = "\n")
}

categorize_runtime <- function(warnings = character(), error_message = "") {
  text <- paste(c(warnings, error_message), collapse = " ")
  if (!nzchar(trimws(text))) {
    return("")
  }
  lower <- tolower(text)
  if (grepl("converg|ncycles|cycle|iteration", lower)) {
    return("convergence_or_cycle_limit")
  }
  if (grepl("singular|hessian|positive definite|invert", lower)) {
    return("information_matrix_or_singularity")
  }
  if (grepl("missing|na|nan|infinite|non-finite", lower)) {
    return("nonfinite_or_missing_numeric")
  }
  if (grepl("category|response|empty", lower)) {
    return("sparse_response_category")
  }
  "other_runtime_message"
}

safe_extract <- function(model, key, default = NA) {
  value <- tryCatch(extract.mirt(model, key), error = function(e) default)
  if (length(value) == 0) {
    return(default)
  }
  value
}

fit_model_for <- function(draw_data, model_id, description, slope_items = character(), threshold_items = character()) {
  warnings <- character()
  syntax <- model_syntax(slope_items, threshold_items)
  model <- mirt.model(syntax)
  current_data <- draw_data[, items]
  current_data[] <- lapply(current_data, function(col) as.integer(col))
  current_group <- factor(draw_data$dataset, levels = c("edaic", "cmdc"))

  result <- tryCatch(
    withCallingHandlers(
      multipleGroup(
        current_data,
        model,
        group = current_group,
        itemtype = rep("graded", length(items)),
        method = "EM",
        quadpts = 31,
        SE = FALSE,
        verbose = FALSE,
        technical = list(NCYCLES = 3000)
      ),
      warning = function(w) {
        warnings <<- c(warnings, conditionMessage(w))
        invokeRestart("muffleWarning")
      }
    ),
    error = function(e) e
  )

  if (inherits(result, "error")) {
    error_message <- conditionMessage(result)
    row <- data.frame(
      model_id = model_id,
      description = description,
      fit_success = FALSE,
      converged = FALSE,
      parameter_count = NA_integer_,
      log_likelihood = NA_real_,
      aic = NA_real_,
      bic = NA_real_,
      iterations = NA_integer_,
      warning_count = length(warnings),
      error_category = categorize_runtime(warnings, error_message),
      stringsAsFactors = FALSE
    )
    return(list(model = NULL, row = row, syntax = syntax))
  }

  row <- data.frame(
    model_id = model_id,
    description = description,
    fit_success = TRUE,
    converged = isTRUE(safe_extract(result, "converged", FALSE)),
    parameter_count = as.integer(safe_extract(result, "nest", NA_integer_)),
    log_likelihood = as.numeric(safe_extract(result, "logLik", NA_real_)),
    aic = as.numeric(safe_extract(result, "AIC", NA_real_)),
    bic = as.numeric(safe_extract(result, "BIC", NA_real_)),
    iterations = as.integer(safe_extract(result, "iterations", NA_integer_)),
    warning_count = length(warnings),
    error_category = categorize_runtime(warnings, ""),
    stringsAsFactors = FALSE
  )
  list(model = result, row = row, syntax = syntax)
}

decision_for <- function(p_value, delta_bic, df) {
  if (is.na(df) || df <= 0) {
    return("not_nested_or_invalid")
  }
  if (!is.na(p_value) && !is.na(delta_bic) && p_value < lrt_alpha && delta_bic > bic_improvement_tol) {
    return("restricted_model_rejected_lrt_and_bic")
  }
  if (!is.na(p_value) && p_value < lrt_alpha) {
    return("restricted_model_rejected_lrt_only")
  }
  if (!is.na(delta_bic) && delta_bic > bic_improvement_tol) {
    return("full_model_preferred_bic_only")
  }
  "no_strong_evidence_against_restriction"
}

lrt_row <- function(tier_id, draw_id, comparison_id, restricted_id, full_id, fit_rows) {
  restricted <- fit_rows[fit_rows$model_id == restricted_id, , drop = FALSE]
  full <- fit_rows[fit_rows$model_id == full_id, , drop = FALSE]
  has_rows <- nrow(restricted) == 1 && nrow(full) == 1
  fit_ok <- has_rows && isTRUE(restricted$fit_success[[1]]) && isTRUE(full$fit_success[[1]])
  convergence_ok <- fit_ok && isTRUE(restricted$converged[[1]]) && isTRUE(full$converged[[1]])
  finite_ok <- convergence_ok &&
    is.finite(restricted$parameter_count[[1]]) && is.finite(full$parameter_count[[1]]) &&
    is.finite(restricted$log_likelihood[[1]]) && is.finite(full$log_likelihood[[1]]) &&
    is.finite(restricted$aic[[1]]) && is.finite(full$aic[[1]]) &&
    is.finite(restricted$bic[[1]]) && is.finite(full$bic[[1]])
  if (!finite_ok) {
    failure_reason <- "comparison_failed_missing_fit"
    if (has_rows && !fit_ok) {
      failure_reason <- "comparison_failed_fit_error"
    } else if (fit_ok && !convergence_ok) {
      failure_reason <- "comparison_failed_nonconverged_fit"
    } else if (convergence_ok && !finite_ok) {
      failure_reason <- "comparison_failed_nonfinite_fit"
    }
    return(data.frame(
      tier_id = tier_id,
      draw_id = draw_id,
      comparison_id = comparison_id,
      restricted_model = restricted_id,
      full_model = full_id,
      restricted_fit_success = if (nrow(restricted) == 1) restricted$fit_success[[1]] else FALSE,
      full_fit_success = if (nrow(full) == 1) full$fit_success[[1]] else FALSE,
      restricted_converged = if (nrow(restricted) == 1) restricted$converged[[1]] else FALSE,
      full_converged = if (nrow(full) == 1) full$converged[[1]] else FALSE,
      comparison_valid = FALSE,
      failure_reason = failure_reason,
      df = NA_integer_,
      lr_statistic = NA_real_,
      p_value = NA_real_,
      delta_aic_restricted_minus_full = NA_real_,
      delta_bic_restricted_minus_full = NA_real_,
      decision = failure_reason,
      stringsAsFactors = FALSE
    ))
  }
  df <- as.integer(full$parameter_count[[1]] - restricted$parameter_count[[1]])
  lr <- max(0, 2 * (full$log_likelihood[[1]] - restricted$log_likelihood[[1]]))
  p_value <- if (!is.na(df) && df > 0) pchisq(lr, df = df, lower.tail = FALSE) else NA_real_
  delta_aic <- restricted$aic[[1]] - full$aic[[1]]
  delta_bic <- restricted$bic[[1]] - full$bic[[1]]
  data.frame(
    tier_id = tier_id,
    draw_id = draw_id,
    comparison_id = comparison_id,
    restricted_model = restricted_id,
    full_model = full_id,
    restricted_fit_success = restricted$fit_success[[1]],
    full_fit_success = full$fit_success[[1]],
    restricted_converged = restricted$converged[[1]],
    full_converged = full$converged[[1]],
    comparison_valid = TRUE,
    failure_reason = "",
    df = df,
    lr_statistic = lr,
    p_value = p_value,
    delta_aic_restricted_minus_full = delta_aic,
    delta_bic_restricted_minus_full = delta_bic,
    decision = decision_for(p_value, delta_bic, df),
    stringsAsFactors = FALSE
  )
}

empty_itemfit_rows <- function(tier_id, draw_id, available = FALSE, error_category = "") {
  rows <- expand.grid(
    dataset = c("edaic", "cmdc"),
    construct_id = items,
    stringsAsFactors = FALSE
  )
  rows$tier_id <- tier_id
  rows$draw_id <- draw_id
  rows$item_label_short <- unname(item_labels[rows$construct_id])
  rows$itemfit_available <- available
  rows$flagged_p_lt_001 <- FALSE
  rows$error_category <- error_category
  rows[, c("tier_id", "draw_id", "dataset", "construct_id", "item_label_short", "itemfit_available", "flagged_p_lt_001", "error_category")]
}

collect_itemfit_rows <- function(tier_id, draw_id, partial_model) {
  if (is.null(partial_model)) {
    return(empty_itemfit_rows(tier_id, draw_id, FALSE, "missing_partial_model"))
  }
  itemfit_result <- tryCatch(as.data.frame(itemfit(partial_model)), error = function(e) e)
  if (inherits(itemfit_result, "error")) {
    return(empty_itemfit_rows(tier_id, draw_id, FALSE, categorize_runtime(character(), conditionMessage(itemfit_result))))
  }
  out <- empty_itemfit_rows(tier_id, draw_id, TRUE, "")
  for (dataset_name in c("edaic", "cmdc")) {
    for (idx in seq_along(items)) {
      p_col <- paste0(dataset_name, ".p.S_X2")
      row_idx <- out$dataset == dataset_name & out$construct_id == items[[idx]]
      if (p_col %in% names(itemfit_result) && idx <= nrow(itemfit_result)) {
        p_value <- suppressWarnings(as.numeric(itemfit_result[idx, p_col]))
        out$flagged_p_lt_001[row_idx] <- is.finite(p_value) && p_value < lrt_alpha
      }
    }
  }
  out
}

draw_sample <- function() {
  sampled <- lapply(levels(responses$dataset), function(dataset_name) {
    group_rows <- responses[responses$dataset == dataset_name, , drop = FALSE]
    group_rows[sample(seq_len(nrow(group_rows)), nrow(group_rows), replace = TRUE), , drop = FALSE]
  })
  out <- do.call(rbind, sampled)
  rownames(out) <- NULL
  out
}

anchors <- roles$construct_id[roles$partial_invariance_role == "anchor_candidate"]
metric_only <- roles$construct_id[roles$partial_invariance_role == "metric_only_threshold_free"]
partial_slope_items <- union(anchors, metric_only)
partial_threshold_items <- anchors

run_core_draw <- function(tier_id, draw_id, draw_data, do_itemfit) {
  fits <- list()
  fits$configural <- fit_model_for(draw_data, "configural", "All loadings and thresholds free by dataset.")
  fits$metric <- fit_model_for(draw_data, "metric", "Loadings constrained equal; thresholds free by dataset.", slope_items = items)
  fits$scalar <- fit_model_for(draw_data, "scalar", "Loadings and thresholds constrained equal by dataset.", slope_items = items, threshold_items = items)
  fits$partial_mv10 <- fit_model_for(
    draw_data,
    "partial_mv10",
    "MV10 partial model with anchor loadings/thresholds constrained and metric-only loadings constrained.",
    slope_items = partial_slope_items,
    threshold_items = partial_threshold_items
  )
  fit_rows <- do.call(rbind, lapply(fits, function(x) x$row))
  fit_rows$tier_id <- tier_id
  fit_rows$draw_id <- draw_id
  fit_rows <- fit_rows[, c("tier_id", "draw_id", setdiff(names(fit_rows), c("tier_id", "draw_id")))]

  comparisons <- do.call(rbind, list(
    lrt_row(tier_id, draw_id, "metric_vs_configural", "metric", "configural", fit_rows),
    lrt_row(tier_id, draw_id, "scalar_vs_metric", "scalar", "metric", fit_rows),
    lrt_row(tier_id, draw_id, "partial_mv10_vs_scalar", "scalar", "partial_mv10", fit_rows),
    lrt_row(tier_id, draw_id, "partial_mv10_vs_configural", "partial_mv10", "configural", fit_rows)
  ))
  itemfit_rows <- if (do_itemfit) {
    collect_itemfit_rows(tier_id, draw_id, fits$partial_mv10$model)
  } else {
    data.frame()
  }
  list(fit_rows = fit_rows, comparisons = comparisons, itemfit_rows = itemfit_rows)
}

run_dif_draw <- function(tier_id, draw_id, draw_data) {
  fits <- list()
  fits$metric <- fit_model_for(draw_data, "metric", "Loading reference model.", slope_items = items)
  fits$scalar <- fit_model_for(draw_data, "scalar", "Threshold reference model.", slope_items = items, threshold_items = items)
  for (item in items) {
    fits[[paste0("loading_free_one_", item)]] <- fit_model_for(
      draw_data,
      paste0("loading_free_one_", item),
      paste("Loading DIF diagnostic for", item),
      slope_items = setdiff(items, item)
    )
    fits[[paste0("threshold_free_one_", item)]] <- fit_model_for(
      draw_data,
      paste0("threshold_free_one_", item),
      paste("Threshold DIF diagnostic for", item),
      slope_items = items,
      threshold_items = setdiff(items, item)
    )
  }
  fit_rows <- do.call(rbind, lapply(fits, function(x) x$row))
  fit_rows$tier_id <- tier_id
  fit_rows$draw_id <- draw_id
  fit_rows <- fit_rows[, c("tier_id", "draw_id", setdiff(names(fit_rows), c("tier_id", "draw_id")))]

  dif_rows <- list()
  for (item in items) {
    loading <- lrt_row(tier_id, draw_id, paste0("loading_dif_", item), "metric", paste0("loading_free_one_", item), fit_rows)
    threshold <- lrt_row(tier_id, draw_id, paste0("threshold_dif_", item), "scalar", paste0("threshold_free_one_", item), fit_rows)
    dif_rows[[length(dif_rows) + 1]] <- data.frame(
      tier_id = tier_id,
      draw_id = draw_id,
      construct_id = item,
      item_label_short = unname(item_labels[[item]]),
      dif_type = "loading",
      decision = loading$decision,
      effective = isTRUE(loading$comparison_valid[[1]]),
      strong_dif_flag = loading$decision == "restricted_model_rejected_lrt_and_bic",
      stringsAsFactors = FALSE
    )
    dif_rows[[length(dif_rows) + 1]] <- data.frame(
      tier_id = tier_id,
      draw_id = draw_id,
      construct_id = item,
      item_label_short = unname(item_labels[[item]]),
      dif_type = "threshold",
      decision = threshold$decision,
      effective = isTRUE(threshold$comparison_valid[[1]]),
      strong_dif_flag = threshold$decision == "restricted_model_rejected_lrt_and_bic",
      stringsAsFactors = FALSE
    )
  }
  list(fit_rows = fit_rows, dif_rows = do.call(rbind, dif_rows))
}

wilson_bounds <- function(k, n) {
  if (is.na(n) || n <= 0) {
    return(c(NA_real_, NA_real_))
  }
  z <- 1.95996398454005
  phat <- k / n
  denom <- 1 + z^2 / n
  center <- (phat + z^2 / (2 * n)) / denom
  half <- z * sqrt((phat * (1 - phat) + z^2 / (4 * n)) / n) / denom
  c(max(0, center - half), min(1, center + half))
}

rate_row <- function(successes, trials, prefix = "") {
  bounds <- wilson_bounds(successes, trials)
  out <- list()
  out[[paste0(prefix, "count")]] <- successes
  out[[paste0(prefix, "rate")]] <- if (trials > 0) successes / trials else NA_real_
  out[[paste0(prefix, "ci_low")]] <- bounds[[1]]
  out[[paste0(prefix, "ci_high")]] <- bounds[[2]]
  out
}

all_fit_rows <- list()
all_comparison_rows <- list()
all_itemfit_rows <- list()
all_dif_rows <- list()
runtime_rows <- list()

run_core_tier <- function(tier_id, requested_R, claim_status) {
  started <- Sys.time()
  for (draw_id in seq_len(requested_R)) {
    result <- run_core_draw(tier_id, draw_id, draw_sample(), collect_itemfit)
    all_fit_rows[[length(all_fit_rows) + 1]] <<- result$fit_rows
    all_comparison_rows[[length(all_comparison_rows) + 1]] <<- result$comparisons
    if (nrow(result$itemfit_rows) > 0) {
      all_itemfit_rows[[length(all_itemfit_rows) + 1]] <<- result$itemfit_rows
    }
  }
  elapsed <- as.numeric(difftime(Sys.time(), started, units = "secs"))
  runtime_rows[[length(runtime_rows) + 1]] <<- data.frame(
    tier_id = tier_id,
    requested_R = requested_R,
    attempted_R = requested_R,
    primary_effective_draws = NA_integer_,
    elapsed_seconds = elapsed,
    claim_status = claim_status,
    status = "complete",
    stringsAsFactors = FALSE
  )
}

run_dif_tier <- function(tier_id, requested_R) {
  started <- Sys.time()
  for (draw_id in seq_len(requested_R)) {
    result <- run_dif_draw(tier_id, draw_id, draw_sample())
    all_fit_rows[[length(all_fit_rows) + 1]] <<- result$fit_rows
    all_dif_rows[[length(all_dif_rows) + 1]] <<- result$dif_rows
  }
  elapsed <- as.numeric(difftime(Sys.time(), started, units = "secs"))
  runtime_rows[[length(runtime_rows) + 1]] <<- data.frame(
    tier_id = tier_id,
    requested_R = requested_R,
    attempted_R = requested_R,
    primary_effective_draws = NA_integer_,
    elapsed_seconds = elapsed,
    claim_status = "primary_anchor_and_DIF_stability",
    status = "complete",
    stringsAsFactors = FALSE
  )
}

if (smoke_R > 0) {
  run_core_tier("MV14_A_smoke_runtime", smoke_R, "not_claimable_smoke")
}
if (core_R > 0) {
  run_core_tier("MV14_B_core_model_stability", core_R, "primary_core_stability")
}
if (dif_R > 0) {
  run_dif_tier("MV14_C_item_DIF_stability", dif_R)
}

fit_rows <- if (length(all_fit_rows) > 0) do.call(rbind, all_fit_rows) else data.frame()
comparison_rows <- if (length(all_comparison_rows) > 0) do.call(rbind, all_comparison_rows) else data.frame()
itemfit_rows <- if (length(all_itemfit_rows) > 0) do.call(rbind, all_itemfit_rows) else data.frame()
dif_rows <- if (length(all_dif_rows) > 0) do.call(rbind, all_dif_rows) else data.frame()

summarize_core <- function(rows) {
  out <- list()
  if (nrow(rows) == 0) {
    return(data.frame())
  }
  for (tier_id in sort(unique(rows$tier_id))) {
    tier_rows <- rows[rows$tier_id == tier_id & rows$model_id %in% core_ids, , drop = FALSE]
    for (model_id in core_ids) {
      model_rows <- tier_rows[tier_rows$model_id == model_id, , drop = FALSE]
      attempted <- nrow(model_rows)
      if (attempted == 0) {
        next
      }
      fit_success <- sum(model_rows$fit_success, na.rm = TRUE)
      converged <- sum(model_rows$fit_success & model_rows$converged, na.rm = TRUE)
      fit_bounds <- wilson_bounds(fit_success, attempted)
      conv_bounds <- wilson_bounds(converged, attempted)
      out[[length(out) + 1]] <- data.frame(
        tier_id = tier_id,
        model_id = model_id,
        attempted_draws = attempted,
        fit_success_draws = fit_success,
        fit_success_rate = if (attempted > 0) fit_success / attempted else NA_real_,
        fit_success_ci_low = fit_bounds[[1]],
        fit_success_ci_high = fit_bounds[[2]],
        converged_draws = converged,
        convergence_rate = if (attempted > 0) converged / attempted else NA_real_,
        convergence_ci_low = conv_bounds[[1]],
        convergence_ci_high = conv_bounds[[2]],
        warning_draws = sum(model_rows$warning_count > 0, na.rm = TRUE),
        error_draws = sum(!model_rows$fit_success, na.rm = TRUE),
        median_iterations = suppressWarnings(median(model_rows$iterations, na.rm = TRUE)),
        p95_iterations = suppressWarnings(as.numeric(quantile(model_rows$iterations, probs = 0.95, na.rm = TRUE, names = FALSE))),
        stringsAsFactors = FALSE
      )
    }
  }
  do.call(rbind, out)
}

summarize_selection_for <- function(rows, model_ids, selection_family) {
  out <- list()
  if (nrow(rows) == 0) {
    return(data.frame())
  }
  for (tier_id in sort(unique(rows$tier_id))) {
    tier_rows <- rows[rows$tier_id == tier_id & rows$model_id %in% model_ids, , drop = FALSE]
    draw_ids <- sort(unique(tier_rows$draw_id))
    choices <- data.frame()
    attempted <- length(draw_ids)
    all_fit_success_draws <- 0L
    all_converged_draws <- 0L
    for (draw_id in draw_ids) {
      draw_rows <- tier_rows[tier_rows$draw_id == draw_id, , drop = FALSE]
      has_all_models <- all(model_ids %in% draw_rows$model_id)
      fit_ok <- has_all_models && all(draw_rows$fit_success)
      convergence_ok <- fit_ok && all(draw_rows$converged)
      finite_ok <- convergence_ok && all(is.finite(draw_rows$aic)) && all(is.finite(draw_rows$bic))
      if (fit_ok) {
        all_fit_success_draws <- all_fit_success_draws + 1L
      }
      if (convergence_ok) {
        all_converged_draws <- all_converged_draws + 1L
      }
      ok <- finite_ok
      if (ok) {
        choices <- rbind(
          choices,
          data.frame(
            criterion = "aic",
            selected_model = draw_rows$model_id[which.min(draw_rows$aic)],
            stringsAsFactors = FALSE
          ),
          data.frame(
            criterion = "bic",
            selected_model = draw_rows$model_id[which.min(draw_rows$bic)],
            stringsAsFactors = FALSE
          )
        )
      }
    }
    for (criterion in c("aic", "bic")) {
      criterion_rows <- choices[choices$criterion == criterion, , drop = FALSE]
      effective <- nrow(criterion_rows)
      if (effective == 0) {
        next
      }
      for (model_id in core_ids) {
        if (!(model_id %in% model_ids)) {
          next
        }
        selected <- sum(criterion_rows$selected_model == model_id)
        bounds <- wilson_bounds(selected, effective)
        out[[length(out) + 1]] <- data.frame(
          tier_id = tier_id,
          selection_family = selection_family,
          criterion = criterion,
          model_id = model_id,
          attempted_draws = attempted,
          all_fit_success_draws = all_fit_success_draws,
          all_converged_draws = all_converged_draws,
          selected_draws = selected,
          effective_draws = effective,
          selection_frequency = if (effective > 0) selected / effective else NA_real_,
          selection_ci_low = bounds[[1]],
          selection_ci_high = bounds[[2]],
          stringsAsFactors = FALSE
        )
      }
    }
  }
  if (length(out) == 0) {
    return(data.frame())
  }
  do.call(rbind, out)
}

summarize_selection <- function(rows) {
  summarize_selection_for(rows, core_ids, "full_ladder_configural_metric_partial_scalar")
}

summarize_stable_ladder_selection <- function(rows) {
  summarize_selection_for(rows, stable_ladder_ids, "stable_ladder_metric_partial_scalar")
}

summarize_decisions <- function(rows) {
  if (nrow(rows) == 0) {
    return(data.frame())
  }
  out <- list()
  keys <- unique(rows[, c("tier_id", "comparison_id")])
  for (idx in seq_len(nrow(keys))) {
    subset_rows <- rows[rows$tier_id == keys$tier_id[[idx]] & rows$comparison_id == keys$comparison_id[[idx]], , drop = FALSE]
    attempted <- nrow(subset_rows)
    valid_comparisons <- sum(subset_rows$comparison_valid, na.rm = TRUE)
    for (decision in sort(unique(subset_rows$decision))) {
      count <- sum(subset_rows$decision == decision)
      bounds <- wilson_bounds(count, attempted)
      valid_count <- if (startsWith(decision, "comparison_failed")) NA_integer_ else count
      valid_bounds <- wilson_bounds(valid_count, valid_comparisons)
      out[[length(out) + 1]] <- data.frame(
        tier_id = keys$tier_id[[idx]],
        comparison_id = keys$comparison_id[[idx]],
        decision = decision,
        decision_draws = count,
        attempted_draws = attempted,
        effective_draws = valid_comparisons,
        failed_draws = attempted - valid_comparisons,
        decision_frequency = if (attempted > 0) count / attempted else NA_real_,
        valid_decision_frequency = if (!is.na(valid_count) && valid_comparisons > 0) valid_count / valid_comparisons else NA_real_,
        decision_ci_low = bounds[[1]],
        decision_ci_high = bounds[[2]],
        valid_decision_ci_low = valid_bounds[[1]],
        valid_decision_ci_high = valid_bounds[[2]],
        stringsAsFactors = FALSE
      )
    }
  }
  do.call(rbind, out)
}

summarize_itemfit <- function(rows) {
  if (nrow(rows) == 0) {
    return(data.frame())
  }
  out <- list()
  keys <- unique(rows[, c("tier_id", "dataset", "construct_id", "item_label_short")])
  for (idx in seq_len(nrow(keys))) {
    subset_rows <- rows[
      rows$tier_id == keys$tier_id[[idx]] &
        rows$dataset == keys$dataset[[idx]] &
        rows$construct_id == keys$construct_id[[idx]],
      ,
      drop = FALSE
    ]
    attempted <- nrow(subset_rows)
    available <- sum(subset_rows$itemfit_available, na.rm = TRUE)
    flagged <- sum(subset_rows$itemfit_available & subset_rows$flagged_p_lt_001, na.rm = TRUE)
    bounds <- wilson_bounds(flagged, available)
    out[[length(out) + 1]] <- data.frame(
      tier_id = keys$tier_id[[idx]],
      dataset = keys$dataset[[idx]],
      construct_id = keys$construct_id[[idx]],
      item_label_short = keys$item_label_short[[idx]],
      attempted_draws = attempted,
      itemfit_available_draws = available,
      flagged_draws = flagged,
      flag_frequency = if (available > 0) flagged / available else NA_real_,
      flag_ci_low = bounds[[1]],
      flag_ci_high = bounds[[2]],
      stringsAsFactors = FALSE
    )
  }
  do.call(rbind, out)
}

summarize_dif <- function(rows) {
  if (nrow(rows) == 0) {
    return(data.frame())
  }
  out <- list()
  tier_id <- "MV14_C_item_DIF_stability"
  for (item in items) {
    loading <- rows[rows$construct_id == item & rows$dif_type == "loading", , drop = FALSE]
    threshold <- rows[rows$construct_id == item & rows$dif_type == "threshold", , drop = FALSE]
    loading_attempted <- nrow(loading)
    threshold_attempted <- nrow(threshold)
    loading_eff <- sum(loading$effective, na.rm = TRUE)
    threshold_eff <- sum(threshold$effective, na.rm = TRUE)
    loading_flag <- sum(loading$effective & loading$strong_dif_flag, na.rm = TRUE)
    threshold_flag <- sum(threshold$effective & threshold$strong_dif_flag, na.rm = TRUE)

    draw_ids <- sort(unique(c(loading$draw_id, threshold$draw_id)))
    support_eff <- 0
    support_count <- 0
    for (draw_id in draw_ids) {
      lrow <- loading[loading$draw_id == draw_id, , drop = FALSE]
      trow <- threshold[threshold$draw_id == draw_id, , drop = FALSE]
      ok <- nrow(lrow) == 1 && nrow(trow) == 1 && isTRUE(lrow$effective[[1]]) && isTRUE(trow$effective[[1]])
      if (ok) {
        support_eff <- support_eff + 1
        if (!isTRUE(lrow$strong_dif_flag[[1]]) && !isTRUE(trow$strong_dif_flag[[1]])) {
          support_count <- support_count + 1
        }
      }
    }
    loading_bounds <- wilson_bounds(loading_flag, loading_eff)
    threshold_bounds <- wilson_bounds(threshold_flag, threshold_eff)
    support_bounds <- wilson_bounds(support_count, support_eff)
    out[[length(out) + 1]] <- data.frame(
      tier_id = tier_id,
      construct_id = item,
      item_label_short = unname(item_labels[[item]]),
      mv10_role = role_for(item),
      loading_attempted_draws = loading_attempted,
      loading_effective_draws = loading_eff,
      loading_failed_draws = loading_attempted - loading_eff,
      loading_flag_draws = loading_flag,
      loading_flag_frequency = if (loading_eff > 0) loading_flag / loading_eff else NA_real_,
      loading_ci_low = loading_bounds[[1]],
      loading_ci_high = loading_bounds[[2]],
      threshold_attempted_draws = threshold_attempted,
      threshold_effective_draws = threshold_eff,
      threshold_failed_draws = threshold_attempted - threshold_eff,
      threshold_flag_draws = threshold_flag,
      threshold_flag_frequency = if (threshold_eff > 0) threshold_flag / threshold_eff else NA_real_,
      threshold_ci_low = threshold_bounds[[1]],
      threshold_ci_high = threshold_bounds[[2]],
      anchor_support_attempted_draws = length(draw_ids),
      anchor_support_effective_draws = support_eff,
      anchor_support_draws = support_count,
      anchor_support_frequency = if (support_eff > 0) support_count / support_eff else NA_real_,
      anchor_support_ci_low = support_bounds[[1]],
      anchor_support_ci_high = support_bounds[[2]],
      stringsAsFactors = FALSE
    )
  }
  out <- do.call(rbind, out)
  out$threshold_frequency_rank <- rank(-out$threshold_flag_frequency, ties.method = "min", na.last = "keep")
  out$loading_frequency_rank <- rank(-out$loading_flag_frequency, ties.method = "min", na.last = "keep")
  out
}

summarize_runtime_messages <- function(rows) {
  if (nrow(rows) == 0) {
    return(data.frame())
  }
  out <- list()
  keys <- unique(rows[, c("tier_id", "model_id")])
  for (idx in seq_len(nrow(keys))) {
    subset_rows <- rows[rows$tier_id == keys$tier_id[[idx]] & rows$model_id == keys$model_id[[idx]], , drop = FALSE]
    categories <- subset_rows$error_category[nzchar(subset_rows$error_category)]
    category <- if (length(categories) == 0) "" else names(sort(table(categories), decreasing = TRUE))[[1]]
    out[[length(out) + 1]] <- data.frame(
      tier_id = keys$tier_id[[idx]],
      model_id = keys$model_id[[idx]],
      attempted_draws = nrow(subset_rows),
      warning_draws = sum(subset_rows$warning_count > 0, na.rm = TRUE),
      error_draws = sum(!subset_rows$fit_success, na.rm = TRUE),
      total_warning_count = sum(subset_rows$warning_count, na.rm = TRUE),
      dominant_runtime_category = category,
      stringsAsFactors = FALSE
    )
  }
  do.call(rbind, out)
}

core_summary <- summarize_core(fit_rows)
selection_summary <- summarize_selection(fit_rows)
stable_ladder_selection_summary <- summarize_stable_ladder_selection(fit_rows)
decision_summary <- summarize_decisions(comparison_rows)
itemfit_summary <- summarize_itemfit(itemfit_rows)
dif_summary <- summarize_dif(dif_rows)
runtime_message_summary <- summarize_runtime_messages(fit_rows)
runtime_summary <- if (length(runtime_rows) > 0) do.call(rbind, runtime_rows) else data.frame()

if (nrow(runtime_summary) > 0) {
  for (idx in seq_len(nrow(runtime_summary))) {
    tier_id <- runtime_summary$tier_id[[idx]]
    if (tier_id %in% selection_summary$tier_id) {
      eff <- selection_summary$effective_draws[selection_summary$tier_id == tier_id & selection_summary$criterion == "aic"]
      runtime_summary$primary_effective_draws[[idx]] <- if (length(eff) > 0) max(eff, na.rm = TRUE) else NA_integer_
    }
    if (tier_id %in% dif_summary$tier_id) {
      eff <- dif_summary$anchor_support_effective_draws[dif_summary$tier_id == tier_id]
      runtime_summary$primary_effective_draws[[idx]] <- if (length(eff) > 0) min(eff, na.rm = TRUE) else NA_integer_
    }
  }
}

optional_summary <- data.frame(
  tier_id = c("MV14_D_boot_mirt_SE_availability", "MV14_E_parametric_LR_sensitivity"),
  status = c("skipped_runtime_bounded_optional", "skipped_runtime_bounded_optional"),
  requested_R = c(0L, 0L),
  aggregate_output_policy = c(
    "finite SE/CI availability counts only if run later",
    "parametric LRT p-value summaries only if run later"
  ),
  reason = c(
    "Default MV14 run prioritizes predeclared core and item-DIF stability before optional parameter bootstrap.",
    "Default MV14 run prioritizes observed bootstrap decision stability before optional boot.LR sensitivity."
  ),
  stringsAsFactors = FALSE
)

runtime_versions <- data.frame(
  component = c("R", "mirt", "lavaan", "Deriv", "GPArotation", "dcurver"),
  version = c(
    R.version.string,
    as.character(packageVersion("mirt")),
    if (requireNamespace("lavaan", quietly = TRUE)) as.character(packageVersion("lavaan")) else "missing",
    as.character(packageVersion("Deriv")),
    as.character(packageVersion("GPArotation")),
    as.character(packageVersion("dcurver"))
  ),
  source = c("system", "CRAN_archive", "ubuntu_r_cran_lavaan", "CRAN_archive", "CRAN", "CRAN"),
  stringsAsFactors = FALSE
)

execution_summary <- data.frame(
  external_engine = "mirt::multipleGroup",
  seed = seed,
  smoke_R = smoke_R,
  core_R = core_R,
  dif_R = dif_R,
  collect_itemfit = collect_itemfit,
  fitted_parameters_exported = FALSE,
  factor_scores_exported = FALSE,
  fitted_model_objects_exported = FALSE,
  bootstrap_draws_exported = FALSE,
  detailed_logs_exported = FALSE,
  stringsAsFactors = FALSE
)

write.csv(core_summary, file.path(out_dir, "core_model_stability_summary.csv"), row.names = FALSE)
write.csv(selection_summary, file.path(out_dir, "model_selection_frequency.csv"), row.names = FALSE)
write.csv(stable_ladder_selection_summary, file.path(out_dir, "stable_ladder_model_selection_frequency.csv"), row.names = FALSE)
write.csv(decision_summary, file.path(out_dir, "invariance_decision_frequency.csv"), row.names = FALSE)
write.csv(itemfit_summary, file.path(out_dir, "itemfit_stability_summary.csv"), row.names = FALSE)
write.csv(dif_summary, file.path(out_dir, "item_dif_stability_summary.csv"), row.names = FALSE)
write.csv(runtime_message_summary, file.path(out_dir, "warning_failure_summary.csv"), row.names = FALSE)
write.csv(runtime_summary, file.path(out_dir, "bootstrap_runtime_summary.csv"), row.names = FALSE)
write.csv(optional_summary, file.path(out_dir, "optional_sensitivity_summary.csv"), row.names = FALSE)
write.csv(runtime_versions, file.path(out_dir, "runtime_versions.csv"), row.names = FALSE)
write.csv(execution_summary, file.path(out_dir, "r_execution_summary.csv"), row.names = FALSE)
