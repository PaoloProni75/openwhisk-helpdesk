# === Libraries ===
library(httr)
library(jsonlite)
library(readr)
library(dplyr)
library(writexl)
library(ggplot2)

# === Configuration ===
openwhisk_endpoint <- "http://15.161.146.166:3233/api/v1/namespaces/guest/actions/helpdesk/orchestrator"
auth_token <- "Basic MjNiYzQ2YjEtNzFmNi00ZWQ1LThjNTQtODE2YWE0ZjhjNTAyOjEyM3pPM3haQ0xyTU42djJCS0sxZFhZRnBYbFBrY2NPRnFtMTJDZEFzTWdSVTRWck5aOWx5R1ZDR3VNREdJd1A="
input_file <- "questions.json"
output_folder <- "openwhisk_runs"

# Summary and Plots
do_summary <- TRUE
do_plots   <- TRUE
do_top20 <- TRUE

ylim_response_ms <- c(0, 10000)
ylim_total_ms    <- c(0, 12000)

# --- DEBUG SETTINGS ---
num_runs <- 30            # number of test runs
limit_questions <- NULL   # for debugging, set max number of questions
pause_seconds <- 1        # seconds between calls
verbose <- TRUE           # set to TRUE for debugging

# Test settings
always_call_llm <- TRUE   # Set to TRUE to force LLM calls instead of KB

# === Utilities ===
ensure_dir <- function(path) {
  if (!dir.exists(path)) dir.create(path, recursive = TRUE, showWarnings = FALSE)
}

# questions.json must be an array of strings
read_questions <- function(path) {
  js <- jsonlite::fromJSON(path)
  if (!is.character(js)) stop('questions.json must be ["q1","q2",...]')
  js
}

# Lenient coercions (avoid accidental NA)
to_chr <- function(v, d=NA_character_) {
  if (is.null(v) || length(v)==0) return(d)
  v <- v[1]; if (is.na(v)) return(d); as.character(v)
}
to_lgl <- function(v, d=NA) {
  if (is.null(v) || length(v)==0) return(d)
  v <- v[1]
  if (is.logical(v)) return(v)
  if (is.numeric(v)) return(v != 0)
  if (is.character(v)) return(tolower(trimws(v)) %in% c("true","t","1","yes","y"))
  d
}
to_num <- function(v, d=NA_real_) {
  if (is.null(v) || length(v)==0) return(d)
  v <- suppressWarnings(as.numeric(v[1])); if (is.na(v)) d else v
}
to_int <- function(v, d=NA_integer_) {
  if (is.null(v) || length(v)==0) return(d)
  v <- suppressWarnings(as.integer(v[1])); if (is.na(v)) d else v
}

# === Invoke OpenWhisk Helpdesk ===
invoke_helpdesk <- function(question) {
  if (verbose) message(sprintf("→ Invoking with question: %s", question))
  
  # Prepare payload
  payload <- list(question = question)
  if (always_call_llm) {
    payload$ALWAYS_CALL_LLM <- "true"
  }
  
  t0 <- proc.time()
  
  # Make HTTP POST request to OpenWhisk
  res <- tryCatch({
    httr::POST(
      url = paste0(openwhisk_endpoint, "?blocking=true&result=true"),
      httr::add_headers(
        "Authorization" = auth_token,
        "Content-Type" = "application/json"
      ),
      body = jsonlite::toJSON(payload, auto_unbox = TRUE),
      encode = "raw",
      timeout = 90
    )
  }, error = function(e) {
    message("HTTP request error: ", e$message)
    return(NULL)
  })
  
  elapsed_ms_client <- as.numeric((proc.time() - t0)["elapsed"]) * 1000
  
  if (is.null(res)) {
    return(data.frame(
      question         = question,
      answer           = NA_character_,
      escalation       = NA,
      confidence       = NA_real_,
      response_time_ms = NA_integer_,
      total_time_ms    = round(elapsed_ms_client, 2),
      source           = NA_character_,
      action           = NA_character_,
      raw_payload      = "HTTP_ERROR",
      stringsAsFactors = FALSE
    ))
  }
  
  if (verbose) {
    message(sprintf("← HTTP Status: %d", httr::status_code(res)))
  }
  
  # Get response content
  raw_payload <- httr::content(res, "text", encoding = "UTF-8")
  if (verbose) message("→ Raw payload: ", substr(raw_payload, 1, 500))
  
  # Handle HTTP errors
  if (httr::status_code(res) != 200) {
    message(sprintf("HTTP Error %d: %s", httr::status_code(res), raw_payload))
    return(data.frame(
      question         = question,
      answer           = NA_character_,
      escalation       = NA,
      confidence       = NA_real_,
      response_time_ms = NA_integer_,
      total_time_ms    = round(elapsed_ms_client, 2),
      source           = NA_character_,
      action           = NA_character_,
      raw_payload      = raw_payload,
      stringsAsFactors = FALSE
    ))
  }
  
  # Parse JSON response
  parsed <- tryCatch({
    jsonlite::fromJSON(raw_payload, simplifyVector = TRUE, simplifyDataFrame = FALSE)
  }, error = function(e) {
    warning(sprintf('Failed to parse JSON for question: "%s" -> %s', question, e$message))
    message("Raw payload: ", raw_payload)
    return(NULL)
  })
  
  # Debug: show parsed structure
  if (verbose && !is.null(parsed)) {
    message("→ Parsed keys: {", paste0(names(parsed), collapse=", "), "}")
    for (key in names(parsed)) {
      val <- parsed[[key]]
      message(sprintf("   %s: %s", key, substr(as.character(val), 1, 100)))
    }
  }
  
  # Extract fields from OpenWhisk response format
  answer_chr <- to_chr(if (!is.null(parsed)) parsed[["answer"]] else NULL)
  esc_lgl    <- to_lgl(if (!is.null(parsed)) parsed[["escalate_to_human"]] else NULL)
  conf_num   <- to_num(if (!is.null(parsed)) parsed[["confidence"]] else NULL)
  src_chr    <- to_chr(if (!is.null(parsed)) parsed[["source"]] else NULL, "unknown")
  
  # OpenWhisk doesn't provide separate response time, so we use total time
  rtms_int   <- round(elapsed_ms_client, 0)
  
  df <- data.frame(
    question         = question,
    answer           = answer_chr,
    escalation       = if (is.na(esc_lgl)) NA_character_ else if (isTRUE(esc_lgl)) "True" else "False",
    confidence       = conf_num,
    action           = src_chr,  # Use source as action (kb/llm)
    response_time_ms = rtms_int,
    total_time_ms    = round(elapsed_ms_client, 2),
    stringsAsFactors = FALSE
  )
  
  if (verbose) {
    message(sprintf("✓ Parsed → answer=%s | total_ms=%s | esc=%s | conf=%s | src=%s",
                    substr(ifelse(is.na(df$answer), "", df$answer), 1, 120),
                    as.character(df$total_time_ms),
                    as.character(df$escalation),
                    as.character(df$confidence),
                    as.character(src_chr)))
  }
  
  df
}

# === Setup ===
ensure_dir(output_folder)
questions <- read_questions(input_file)
if (!is.null(limit_questions) && limit_questions > 0) {
  total_q <- length(questions)
  questions <- head(questions, limit_questions)
  message(sprintf("Testing with first %d questions (of %d total).", length(questions), total_q))
}

# Execute runs 
for (run_idx in seq_len(num_runs)) {
  message(sprintf("=== Starting run %d/%d ===", run_idx, num_runs))
  run_rows <- vector("list", length(questions))

  for (q_idx in seq_along(questions)) {
    q <- questions[[q_idx]]
    message(sprintf("[%d/%d] Q: %s", q_idx, length(questions), q))

    result <- invoke_helpdesk(q)
    message(sprintf("← Answer: %s", substr(ifelse(is.na(result$answer[1]), "", result$answer[1]), 1, 200)))

    run_rows[[q_idx]] <- result
    Sys.sleep(pause_seconds)
  }

  # Build data frame and select columns in the desired order
  df_run <- bind_rows(run_rows) |>
    dplyr::select(question, answer, escalation, confidence, action, response_time_ms, total_time_ms)

  # Define output path BEFORE writing
  csv_path <- file.path(output_folder, sprintf("openwhisk_run%d.csv", run_idx))

  if (verbose) {
    message("Preview of rows to be written:")
    print(utils::head(df_run, 2))
  }

  # Write once, with minimal quoting and empty string for NA
  readr::write_csv(df_run, csv_path, na = "")

  message(sprintf("=== Completed run %d/%d → %s ===", run_idx, num_runs, csv_path))
}

message("Done. Files written to: ", normalizePath(output_folder))

# === Analysis and Plotting Section ===
csv_files <- list.files(output_folder, pattern = "\\.csv$", full.names = TRUE)

if (do_summary) {
  results <- lapply(csv_files, function(file) {
    df <- readr::read_csv(file, show_col_types = FALSE)
    data.frame(
      Run = basename(file),
      `# Questions`                = nrow(df),
      `Mean Response Time (ms)`    = round(mean(df$response_time_ms, na.rm = TRUE), 2),
      `Std Dev Response Time (ms)` = round(sd(df$response_time_ms, na.rm = TRUE), 2),
      `Min Response Time (ms)`     = round(min(df$response_time_ms, na.rm = TRUE), 2),
      `Max Response Time (ms)`     = round(max(df$response_time_ms, na.rm = TRUE), 2),
      `Mean Total Time (ms)`       = round(mean(df$total_time_ms, na.rm = TRUE), 2),
      `Std Dev Total Time (ms)`    = round(sd(df$total_time_ms, na.rm = TRUE), 2),
      `Min Total Time (ms)`        = round(min(df$total_time_ms, na.rm = TRUE), 2),
      `Max Total Time (ms)`        = round(max(df$total_time_ms, na.rm = TRUE), 2)
    )
  })
  summary_df <- dplyr::bind_rows(results)
  writexl::write_xlsx(summary_df, "OpenWhisk_AnalysisPerFile.xlsx")
  message("Summary written to OpenWhisk_AnalysisPerFile.xlsx")
}

if (do_plots) {
  if (length(csv_files) > 0) {
    df_all <- dplyr::bind_rows(lapply(seq_along(csv_files), function(i) {
      readr::read_csv(csv_files[i], show_col_types = FALSE) %>%
         dplyr::mutate(run = as.factor(i))
    }))
    # filtra NA per evitare warning
    df_all <- df_all %>%
       dplyr::filter(is.finite(response_time_ms), is.finite(total_time_ms))
  
    pdf("openwhisk_response_time_distribution_boxplot.pdf", width = 11, height = 8.5)
  
    p1 <- ggplot2::ggplot(df_all, ggplot2::aes(x = run, y = response_time_ms)) +
      ggplot2::geom_boxplot(fill = "#2c7fb8", alpha = 0.6, outlier.color = "red", na.rm = TRUE) +
      ggplot2::coord_cartesian(ylim = ylim_response_ms) +
      ggplot2::labs(title = "OpenWhisk Helpdesk Response Time (ms) Across 30 Runs", 
                    x = "Run", y = "Response Time (ms)") +
      ggplot2::theme_minimal()
    print(p1)
  
    p2 <- ggplot2::ggplot(df_all, ggplot2::aes(x = run, y = total_time_ms)) +
      ggplot2::geom_boxplot(fill = "#41ab5d", alpha = 0.6, outlier.color = "darkgreen", na.rm = TRUE) +
      ggplot2::coord_cartesian(ylim = ylim_total_ms) +
      ggplot2::labs(title = "Total Time (ms) Including HTTP Overhead",
                       x = "Run", y = "Total Time (ms)") +
      ggplot2::theme_minimal()
    print(p2)
  
    dev.off()
    message("Plots written to openwhisk_response_time_distribution_boxplot.pdf")
   }
}

if (do_top20) {
  if (length(csv_files) > 0) {
    df_all <- dplyr::bind_rows(lapply(csv_files, function(f) {
      readr::read_csv(f, show_col_types = FALSE)
    }))

    agg <- df_all %>%
      dplyr::group_by(question) %>%
      dplyr::summarise(
        mean_response = mean(response_time_ms, na.rm = TRUE),
        sd_response   = sd(response_time_ms,   na.rm = TRUE),
        mean_total    = mean(total_time_ms,    na.rm = TRUE),
        sd_total      = sd(total_time_ms,      na.rm = TRUE),
        n = dplyr::n(),
        .groups = "drop"
      )

    top_mean_resp  <- agg |> dplyr::filter(!is.na(mean_response)) |> dplyr::arrange(dplyr::desc(mean_response)) |> dplyr::slice_head(n = 20)
    top_sd_resp    <- agg |> dplyr::filter(!is.na(sd_response))   |> dplyr::arrange(dplyr::desc(sd_response))   |> dplyr::slice_head(n = 20)
    top_mean_total <- agg |> dplyr::filter(!is.na(mean_total))    |> dplyr::arrange(dplyr::desc(mean_total))    |> dplyr::slice_head(n = 20)
    top_sd_total   <- agg |> dplyr::filter(!is.na(sd_total))      |> dplyr::arrange(dplyr::desc(sd_total))      |> dplyr::slice_head(n = 20)

    pdf("openwhisk_top20_response_and_total_times.pdf", width = 11, height = 8.5)

    p1 <- ggplot2::ggplot(top_mean_resp,
                          ggplot2::aes(x = stats::reorder(question, mean_response), y = mean_response)) +
      ggplot2::geom_col(fill = "#2c7fb8") +
      ggplot2::coord_flip() +
      ggplot2::labs(title = "Top 20 questions with highest average OpenWhisk response time",
                    x = NULL, y = "Average response time (ms)") +
      ggplot2::theme_minimal()
    print(p1)

    p2 <- ggplot2::ggplot(top_sd_resp,
                          ggplot2::aes(x = stats::reorder(question, sd_response), y = sd_response)) +
      ggplot2::geom_col(fill = "#2c7fb8") +
      ggplot2::coord_flip() +
      ggplot2::labs(title = "Top 20 questions with highest variability in OpenWhisk response time",
                    x = NULL, y = "Standard deviation (ms)") +
      ggplot2::theme_minimal()
    print(p2)

    p3 <- ggplot2::ggplot(top_mean_total,
                          ggplot2::aes(x = stats::reorder(question, mean_total), y = mean_total)) +
      ggplot2::geom_col(fill = "#41ab5d") +
      ggplot2::coord_flip() +
      ggplot2::labs(title = "Top 20 questions with highest total elapsed time",
                    x = NULL, y = "Average total time (ms)") +
      ggplot2::theme_minimal()
    print(p3)

    p4 <- ggplot2::ggplot(top_sd_total,
                          ggplot2::aes(x = stats::reorder(question, sd_total), y = sd_total)) +
      ggplot2::geom_col(fill = "#41ab5d") +
      ggplot2::coord_flip() +
      ggplot2::labs(title = "Top 20 questions with highest variability in total elapsed time",
                    x = NULL, y = "Standard deviation (ms)") +
      ggplot2::theme_minimal()
    print(p4)

    dev.off()
    message("Top 20 analysis plots written to openwhisk_top20_response_and_total_times.pdf")
  }
}

message("Analysis complete!")