suppressPackageStartupMessages(library(mirt))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) {
  stop("usage: Rscript phase5_run_mv13_external_psychometric_replication.R <input_csv> <mv10_roles_csv> <out_dir>")
}

input_csv <- args[[1]]
roles_csv <- args[[2]]
out_dir <- args[[3]]
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

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

responses <- read.csv(input_csv, stringsAsFactors = FALSE, check.names = FALSE)
roles <- read.csv(roles_csv, stringsAsFactors = FALSE)

missing_items <- setdiff(items, names(responses))
if (length(missing_items) > 0) {
  stop(paste("missing item columns:", paste(missing_items, collapse = ",")))
}

data <- responses[, items]
data[] <- lapply(data, function(col) as.integer(col))
group <- factor(responses$dataset, levels = c("edaic", "cmdc"))
itemtype <- rep("graded", length(items))

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

latent_invariance_terms <- function(threshold_items = character()) {
  if (length(threshold_items) == 0) {
    return(character())
  }
  unique(c(threshold_items, "free_means", "free_var"))
}

latent_hyperparameter_policy <- function(invariance_terms = character()) {
  if (all(c("free_means", "free_var") %in% invariance_terms)) {
    return("anchor_linked_focal_mean_variance_free")
  }
  "reference_and_focal_hyperparameters_fixed"
}

fit_model <- function(model_id, description, slope_items = character(), threshold_items = character(), se = FALSE) {
  warnings <- character()
  syntax <- model_syntax(slope_items, threshold_items)
  invariance_terms <- latent_invariance_terms(threshold_items)
  hyperparameter_policy <- latent_hyperparameter_policy(invariance_terms)
  model <- mirt.model(syntax)
  result <- tryCatch(
    withCallingHandlers(
      {
        mg_args <- list(
          data = data,
          model = model,
          group = group,
          itemtype = itemtype,
          method = "EM",
          quadpts = 31,
          SE = se,
          verbose = FALSE,
          technical = list(NCYCLES = 3000)
        )
        if (length(invariance_terms) > 0) {
          mg_args$invariance <- invariance_terms
        }
        do.call(multipleGroup, mg_args)
      },
      warning = function(w) {
        warnings <<- c(warnings, conditionMessage(w))
        invokeRestart("muffleWarning")
      }
    ),
    error = function(e) e
  )

  if (inherits(result, "error")) {
    row <- data.frame(
      model_id = model_id,
      description = description,
      fit_success = FALSE,
      converged = FALSE,
      parameter_count = NA_integer_,
      log_likelihood = NA_real_,
      aic = NA_real_,
      bic = NA_real_,
      sabic = NA_real_,
      hq = NA_real_,
      iterations = NA_integer_,
      warning_count = length(warnings),
      warnings = paste(unique(warnings), collapse = " | "),
      error_message = conditionMessage(result),
      mirt_invariance_terms = paste(invariance_terms, collapse = ";"),
      latent_hyperparameter_policy = hyperparameter_policy,
      fitted_parameters_exported = FALSE,
      stringsAsFactors = FALSE
    )
    return(list(model = NULL, row = row, syntax = syntax, invariance = invariance_terms, warnings = warnings))
  }

  row <- data.frame(
    model_id = model_id,
    description = description,
    fit_success = TRUE,
    converged = isTRUE(extract.mirt(result, "converged")),
    parameter_count = as.integer(extract.mirt(result, "nest")),
    log_likelihood = as.numeric(extract.mirt(result, "logLik")),
    aic = as.numeric(extract.mirt(result, "AIC")),
    bic = as.numeric(extract.mirt(result, "BIC")),
    sabic = as.numeric(extract.mirt(result, "SABIC")),
    hq = as.numeric(extract.mirt(result, "HQ")),
    iterations = as.integer(extract.mirt(result, "iterations")),
    warning_count = length(warnings),
    warnings = paste(unique(warnings), collapse = " | "),
    error_message = "",
    mirt_invariance_terms = paste(invariance_terms, collapse = ";"),
    latent_hyperparameter_policy = hyperparameter_policy,
    fitted_parameters_exported = FALSE,
    stringsAsFactors = FALSE
  )
  list(model = result, row = row, syntax = syntax, invariance = invariance_terms, warnings = warnings)
}

lrt_row <- function(comparison_id, restricted_id, full_id, fit_rows, fits, interpretation) {
  restricted_row <- fit_rows[fit_rows$model_id == restricted_id, , drop = FALSE]
  full_row <- fit_rows[fit_rows$model_id == full_id, , drop = FALSE]
  ok <- isTRUE(restricted_row$fit_success[[1]]) && isTRUE(full_row$fit_success[[1]])
  if (!ok) {
    return(data.frame(
      comparison_id = comparison_id,
      restricted_model = restricted_id,
      full_model = full_id,
      restricted_parameter_count = NA_integer_,
      full_parameter_count = NA_integer_,
      df = NA_integer_,
      lr_statistic = NA_real_,
      p_value = NA_real_,
      delta_aic_restricted_minus_full = NA_real_,
      delta_bic_restricted_minus_full = NA_real_,
      decision = "comparison_failed_missing_fit",
      interpretation = interpretation,
      stringsAsFactors = FALSE
    ))
  }

  df <- as.integer(full_row$parameter_count[[1]] - restricted_row$parameter_count[[1]])
  lr <- max(0, 2 * (full_row$log_likelihood[[1]] - restricted_row$log_likelihood[[1]]))
  p_value <- if (df > 0) pchisq(lr, df = df, lower.tail = FALSE) else NA_real_
  delta_aic <- restricted_row$aic[[1]] - full_row$aic[[1]]
  delta_bic <- restricted_row$bic[[1]] - full_row$bic[[1]]
  if (is.na(df) || df <= 0) {
    decision <- "not_nested_or_invalid"
  } else if (!is.na(p_value) && p_value < lrt_alpha && delta_bic > bic_improvement_tol) {
    decision <- "restricted_model_rejected_lrt_and_bic"
  } else if (!is.na(p_value) && p_value < lrt_alpha) {
    decision <- "restricted_model_rejected_lrt_only"
  } else if (delta_bic > bic_improvement_tol) {
    decision <- "full_model_preferred_bic_only"
  } else {
    decision <- "no_strong_evidence_against_restriction"
  }
  data.frame(
    comparison_id = comparison_id,
    restricted_model = restricted_id,
    full_model = full_id,
    restricted_parameter_count = as.integer(restricted_row$parameter_count[[1]]),
    full_parameter_count = as.integer(full_row$parameter_count[[1]]),
    df = df,
    lr_statistic = lr,
    p_value = p_value,
    delta_aic_restricted_minus_full = delta_aic,
    delta_bic_restricted_minus_full = delta_bic,
    decision = decision,
    interpretation = interpretation,
    stringsAsFactors = FALSE
  )
}

nonnested_row <- function(comparison_id, left_id, right_id, fit_rows, interpretation) {
  left <- fit_rows[fit_rows$model_id == left_id, , drop = FALSE]
  right <- fit_rows[fit_rows$model_id == right_id, , drop = FALSE]
  ok <- isTRUE(left$fit_success[[1]]) && isTRUE(right$fit_success[[1]])
  if (!ok) {
    decision <- "comparison_failed_missing_fit"
    delta_aic <- NA_real_
    delta_bic <- NA_real_
  } else {
    delta_aic <- left$aic[[1]] - right$aic[[1]]
    delta_bic <- left$bic[[1]] - right$bic[[1]]
    aic_pref <- if (abs(delta_aic) <= bic_improvement_tol) "similar" else if (left$aic[[1]] < right$aic[[1]]) left_id else right_id
    bic_pref <- if (abs(delta_bic) <= bic_improvement_tol) "similar" else if (left$bic[[1]] < right$bic[[1]]) left_id else right_id
    decision <- paste0("nonnested_bic_prefers_", bic_pref, "_aic_prefers_", aic_pref)
  }
  data.frame(
    comparison_id = comparison_id,
    restricted_model = left_id,
    full_model = right_id,
    restricted_parameter_count = if (ok) as.integer(left$parameter_count[[1]]) else NA_integer_,
    full_parameter_count = if (ok) as.integer(right$parameter_count[[1]]) else NA_integer_,
    df = NA_integer_,
    lr_statistic = NA_real_,
    p_value = NA_real_,
    delta_aic_restricted_minus_full = delta_aic,
    delta_bic_restricted_minus_full = delta_bic,
    decision = decision,
    interpretation = interpretation,
    stringsAsFactors = FALSE
  )
}

all_items <- items
anchors <- roles$construct_id[roles$partial_invariance_role == "anchor_candidate"]
metric_only <- roles$construct_id[roles$partial_invariance_role == "metric_only_threshold_free"]
free_items <- roles$construct_id[roles$partial_invariance_role == "free_loading_or_threshold"]
partial_slope_items <- union(anchors, metric_only)
partial_threshold_items <- anchors

fits <- list()
fits$configural <- fit_model("configural", "All loadings and thresholds free by dataset.")
fits$metric <- fit_model("metric", "Loadings constrained equal; thresholds free by dataset.", slope_items = all_items)
fits$scalar <- fit_model("scalar", "Loadings and thresholds constrained equal by dataset.", slope_items = all_items, threshold_items = all_items)
fits$partial_mv10 <- fit_model(
  "partial_mv10",
  "MV10 partial model: anchor loadings/thresholds constrained, metric-only items constrain loadings, C08 free.",
  slope_items = partial_slope_items,
  threshold_items = partial_threshold_items
)

for (item in items) {
  fits[[paste0("loading_free_one_", item)]] <- fit_model(
    paste0("loading_free_one_", item),
    paste("Loading DIF diagnostic for", item),
    slope_items = setdiff(all_items, item)
  )
  fits[[paste0("threshold_free_one_", item)]] <- fit_model(
    paste0("threshold_free_one_", item),
    paste("Threshold DIF diagnostic for", item),
    slope_items = all_items,
    threshold_items = setdiff(all_items, item)
  )
}

fit_rows <- do.call(rbind, lapply(fits, function(x) x$row))
fit_rows <- fit_rows[order(fit_rows$model_id), ]
write.csv(fit_rows, file.path(out_dir, "fit_model_summary.csv"), row.names = FALSE)

comparisons <- do.call(rbind, list(
  lrt_row(
    "metric_vs_configural",
    "metric",
    "configural",
    fit_rows,
    fits,
    "Tests whether equal loadings lose fit relative to fully free loadings and thresholds."
  ),
  lrt_row(
    "scalar_vs_metric",
    "scalar",
    "metric",
    fit_rows,
    fits,
    "Tests whether equal thresholds lose fit after equal loadings."
  ),
  lrt_row(
    "partial_mv10_vs_scalar",
    "scalar",
    "partial_mv10",
    fit_rows,
    fits,
    "Tests whether MV10 partial freeing improves over full scalar/threshold invariance."
  ),
  lrt_row(
    "partial_mv10_vs_configural",
    "partial_mv10",
    "configural",
    fit_rows,
    fits,
    "Tests whether MV10 partial constraints still lose fit relative to the fully free configural model."
  ),
  nonnested_row(
    "partial_mv10_vs_metric_nonnested",
    "partial_mv10",
    "metric",
    fit_rows,
    "AIC/BIC comparison only: MV10 partial frees C08 loading but constrains anchor thresholds, so it is not nested with the metric model."
  )
))
write.csv(comparisons, file.path(out_dir, "invariance_comparison_summary.csv"), row.names = FALSE)

item_dif_rows <- list()
for (item in items) {
  loading <- lrt_row(
    paste0("loading_dif_", item),
    "metric",
    paste0("loading_free_one_", item),
    fit_rows,
    fits,
    "Item loading freed by dataset against the metric model."
  )
  threshold <- lrt_row(
    paste0("threshold_dif_", item),
    "scalar",
    paste0("threshold_free_one_", item),
    fit_rows,
    fits,
    "Item thresholds freed by dataset against the scalar model."
  )
  item_dif_rows[[length(item_dif_rows) + 1]] <- data.frame(
    construct_id = item,
    item_label_short = unname(item_labels[[item]]),
    dif_type = "loading",
    reference_model = loading$restricted_model,
    freed_model = loading$full_model,
    df = loading$df,
    lr_statistic = loading$lr_statistic,
    p_value = loading$p_value,
    delta_bic_restricted_minus_freed = loading$delta_bic_restricted_minus_full,
    strong_dif_flag = loading$decision == "restricted_model_rejected_lrt_and_bic",
    decision = loading$decision,
    stringsAsFactors = FALSE
  )
  item_dif_rows[[length(item_dif_rows) + 1]] <- data.frame(
    construct_id = item,
    item_label_short = unname(item_labels[[item]]),
    dif_type = "threshold",
    reference_model = threshold$restricted_model,
    freed_model = threshold$full_model,
    df = threshold$df,
    lr_statistic = threshold$lr_statistic,
    p_value = threshold$p_value,
    delta_bic_restricted_minus_freed = threshold$delta_bic_restricted_minus_full,
    strong_dif_flag = threshold$decision == "restricted_model_rejected_lrt_and_bic",
    decision = threshold$decision,
    stringsAsFactors = FALSE
  )
}
item_dif <- do.call(rbind, item_dif_rows)
write.csv(item_dif, file.path(out_dir, "item_dif_lrt_summary.csv"), row.names = FALSE)

anchor_rows <- list()
for (item in items) {
  item_rows <- item_dif[item_dif$construct_id == item, , drop = FALSE]
  loading_row <- item_rows[item_rows$dif_type == "loading", , drop = FALSE]
  threshold_row <- item_rows[item_rows$dif_type == "threshold", , drop = FALSE]
  loading_flag <- isTRUE(loading_row$strong_dif_flag[[1]])
  threshold_flag <- isTRUE(threshold_row$strong_dif_flag[[1]])
  formal_role <- if (!loading_flag && !threshold_flag) {
    "external_anchor_supported"
  } else if (!loading_flag && threshold_flag) {
    "external_metric_only_threshold_free"
  } else {
    "external_free_loading_or_threshold"
  }
  mv10_role <- role_for(item)
  anchor_rows[[length(anchor_rows) + 1]] <- data.frame(
    construct_id = item,
    item_label_short = unname(item_labels[[item]]),
    mv10_role = mv10_role,
    external_role = formal_role,
    mv10_anchor_confirmed = mv10_role == "anchor_candidate" && formal_role == "external_anchor_supported",
    loading_dif_flag = loading_flag,
    threshold_dif_flag = threshold_flag,
    loading_lrt_p_value = loading_row$p_value[[1]],
    threshold_lrt_p_value = threshold_row$p_value[[1]],
    loading_delta_bic_restricted_minus_freed = loading_row$delta_bic_restricted_minus_freed[[1]],
    threshold_delta_bic_restricted_minus_freed = threshold_row$delta_bic_restricted_minus_freed[[1]],
    stringsAsFactors = FALSE
  )
}
anchors_out <- do.call(rbind, anchor_rows)
write.csv(anchors_out, file.path(out_dir, "anchor_confirmation_summary.csv"), row.names = FALSE)

itemfit_status <- "not_available"
itemfit_message <- ""
itemfit_out <- expand.grid(
  dataset = c("edaic", "cmdc"),
  item = items,
  stringsAsFactors = FALSE
)
itemfit_out$item_label_short <- unname(item_labels[itemfit_out$item])
itemfit_out$itemfit_available <- FALSE
itemfit_out$s_x2 <- NA_real_
itemfit_out$df_s_x2 <- NA_real_
itemfit_out$rmsea_s_x2 <- NA_real_
itemfit_out$p_value <- NA_real_
itemfit_out$flagged_p_lt_001 <- NA
if (!is.null(fits$partial_mv10$model)) {
  itemfit_result <- tryCatch(as.data.frame(itemfit(fits$partial_mv10$model)), error = function(e) e)
  if (!inherits(itemfit_result, "error")) {
    itemfit_status <- "available"
    stat_cols <- setdiff(names(itemfit_result), c("item", "itemnames"))
    for (dataset_name in c("edaic", "cmdc")) {
      for (idx in seq_along(items)) {
        row_idx <- itemfit_out$dataset == dataset_name & itemfit_out$item == items[[idx]]
        itemfit_out$itemfit_available[row_idx] <- TRUE
        for (pair in list(
          c("s_x2", paste0(dataset_name, ".S_X2")),
          c("df_s_x2", paste0(dataset_name, ".df.S_X2")),
          c("rmsea_s_x2", paste0(dataset_name, ".RMSEA.S_X2")),
          c("p_value", paste0(dataset_name, ".p.S_X2"))
        )) {
          target <- pair[[1]]
          source <- pair[[2]]
          if (source %in% names(itemfit_result) && idx <= nrow(itemfit_result)) {
            itemfit_out[row_idx, target] <- suppressWarnings(as.numeric(itemfit_result[idx, source]))
          }
        }
        p_value <- itemfit_out$p_value[row_idx]
        if (length(p_value) == 1 && is.finite(p_value)) {
          itemfit_out$flagged_p_lt_001[row_idx] <- p_value < lrt_alpha
        }
      }
    }
    if (length(stat_cols) > 0) {
      itemfit_message <- paste("columns:", paste(stat_cols, collapse = ";"))
    }
  } else {
    itemfit_status <- "failed"
    itemfit_message <- conditionMessage(itemfit_result)
  }
}
write.csv(itemfit_out, file.path(out_dir, "item_fit_summary.csv"), row.names = FALSE)

ci_row <- data.frame(
  model_id = "partial_mv10",
  se_requested = TRUE,
  se_fit_success = FALSE,
  se_converged = FALSE,
  parameter_count = NA_integer_,
  vcov_available = FALSE,
  finite_se_count = NA_integer_,
  ci_value_export_policy = "local_only_full_parameter_ci_not_tracked",
  error_message = "",
  stringsAsFactors = FALSE
)
se_fit <- fit_model(
  "partial_mv10_se",
  "MV10 partial model refit with standard errors for aggregate CI availability only.",
  slope_items = partial_slope_items,
  threshold_items = partial_threshold_items,
  se = TRUE
)
if (!is.null(se_fit$model)) {
  vc <- tryCatch(extract.mirt(se_fit$model, "vcov"), error = function(e) e)
  pv <- tryCatch(extract.mirt(se_fit$model, "parvec"), error = function(e) e)
  ci_row$se_fit_success <- TRUE
  ci_row$se_converged <- isTRUE(extract.mirt(se_fit$model, "converged"))
  ci_row$parameter_count <- as.integer(extract.mirt(se_fit$model, "nest"))
  if (!inherits(vc, "error") && !inherits(pv, "error")) {
    diag_v <- diag(vc)
    finite <- is.finite(diag_v) & diag_v >= 0
    ci_row$vcov_available <- TRUE
    ci_row$finite_se_count <- sum(finite)
  }
} else {
  ci_row$error_message <- se_fit$row$error_message[[1]]
}
write.csv(ci_row, file.path(out_dir, "parameter_ci_availability_summary.csv"), row.names = FALSE)

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
write.csv(runtime_versions, file.path(out_dir, "runtime_versions.csv"), row.names = FALSE)

model_syntax_rows <- do.call(rbind, lapply(names(fits), function(name) {
  data.frame(
    model_id = name,
    mirt_model_syntax = fits[[name]]$syntax,
    mirt_invariance_terms = paste(fits[[name]]$invariance, collapse = ";"),
    latent_hyperparameter_policy = latent_hyperparameter_policy(fits[[name]]$invariance),
    stringsAsFactors = FALSE
  )
}))
write.csv(model_syntax_rows, file.path(out_dir, "external_model_syntax_summary.csv"), row.names = FALSE)

execution_summary <- data.frame(
  external_engine = "mirt::multipleGroup",
  mirt_version = as.character(packageVersion("mirt")),
  anchor_linked_focal_hyperparameters_corrected = any(
    fit_rows$latent_hyperparameter_policy == "anchor_linked_focal_mean_variance_free",
    na.rm = TRUE
  ),
  fit_rows = nrow(fit_rows),
  core_fit_success_count = sum(fit_rows$model_id %in% c("configural", "metric", "scalar", "partial_mv10") & fit_rows$fit_success),
  all_core_converged = all(fit_rows$converged[fit_rows$model_id %in% c("configural", "metric", "scalar", "partial_mv10")]),
  itemfit_status = itemfit_status,
  itemfit_message = itemfit_message,
  parameter_ci_status = if (isTRUE(ci_row$se_fit_success)) "available_aggregate_only" else "failed_or_unavailable",
  full_parameter_table_exported = FALSE,
  factor_scores_exported = FALSE,
  fitted_model_objects_exported = FALSE,
  stringsAsFactors = FALSE
)
write.csv(execution_summary, file.path(out_dir, "r_execution_summary.csv"), row.names = FALSE)
