# Prospective design analysis for the AXB study (Kirby & Sonderegger 2018 style)
#
# Question it answers: with N Hindi-L1 listeners and K contrasts, how often does
# adding the L1 predictor (same Hindi category, i.e. PAM single-category) to a
# distance-only model significantly improve fit, and how much would a significant
# estimate exaggerate the true effect (Type M) or get its sign wrong (Type S)?
#
# Model simulated (trial level, logit link):
#   correct ~ dist_z + merged + (1 + merged | subj) + (1 | contrast) + (1 | item)
# Test: likelihood-ratio test of `merged`, distance-only vs distance + L1.
#
# Run:  Rscript power_sim.R [nsim] [cores]
suppressPackageStartupMessages({ library(lme4); library(parallel) })

args  <- commandArgs(trailingOnly = TRUE)
NSIM  <- if (length(args) >= 1) as.integer(args[1]) else 200
CORES <- if (length(args) >= 2) as.integer(args[2]) else max(1, detectCores() - 1)
set.seed(30004064)

# ---- design constants -------------------------------------------------------
ORDERS        <- 4      # AXB orders per minimal pair: AAB, ABB, BAA, BBA
PAIRS_PER_CON <- 6      # minimal pairs (items) per contrast
TARGET_TRIALS <- 240    # ~20 min of AXB at ~4-5 s per trial

# ---- assumed effect sizes and variability (logit scale) ---------------------
B0       <- 2.2   # accuracy ~90% for a non-merged contrast of average distance
B_DIST   <- 0.20  # per SD of feature distance: farther = slightly easier
SD_SUBJ  <- 0.60  # listeners differ in overall accuracy
SD_SLOPE <- 0.60  # listeners differ in how much a merged contrast hurts
SD_CON   <- 0.40  # contrast-level noise not explained by distance or L1
SD_ITEM  <- 0.30  # minimal pairs differ within a contrast

# The contrast set. K = 3 is the locked set; K = 8 and 12 are expanded sets.
# dist = differing PanPhon features /24 (Hamming, from phonosim /
# icphs2027/results/pair_predictors.csv); merged = both English phones map to
# one Hindi category under hindi_inventory_v2.yaml. Under v2 only v-w and
# zh-dzh are merged, so expanding the set adds mostly non-merged contrasts.
contrast_pool <- data.frame(
  contrast = c("p-ph", "v-w", "r_retro-r_approx",          # locked (Term 1)
               "zh-dzh", "th-t", "dh-d", "z-dzh", "s-sh",    # K = 8
               "f-p", "w-b", "z-s", "th-s"),                 # K = 12
  dist     = c(1, 7, 6, 2, 2, 2, 4, 2, 2, 7, 1, 2),
  merged   = c(0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0)
)

make_design <- function(n_subj, K) {
  cons <- contrast_pool[seq_len(K), ]
  reps <- max(1, round(TARGET_TRIALS / (K * PAIRS_PER_CON * ORDERS)))
  items <- expand.grid(pair = seq_len(PAIRS_PER_CON), contrast = cons$contrast,
                       stringsAsFactors = FALSE)
  items$item <- paste(items$contrast, items$pair, sep = "_")
  items <- merge(items, cons, by = "contrast")
  trials <- items[rep(seq_len(nrow(items)), each = ORDERS * reps), ]
  d <- merge(data.frame(subj = seq_len(n_subj)), trials, by = NULL)
  d$dist_z <- (d$dist - mean(cons$dist)) / ifelse(sd(cons$dist) > 0, sd(cons$dist), 1)
  d
}

simulate_once <- function(d, b_l1, K) {
  subj <- unique(d$subj); cons <- unique(d$contrast); its <- unique(d$item)
  u0 <- rnorm(length(subj), 0, SD_SUBJ);  names(u0) <- subj
  u1 <- rnorm(length(subj), 0, SD_SLOPE); names(u1) <- subj
  uc <- rnorm(length(cons), 0, SD_CON);   names(uc) <- cons
  ui <- rnorm(length(its),  0, SD_ITEM);  names(ui) <- its
  s <- as.character(d$subj)
  eta <- B0 + u0[s] + B_DIST * d$dist_z + (b_l1 + u1[s]) * d$merged +
         uc[d$contrast] + ui[d$item]
  d$correct <- rbinom(nrow(d), 1, plogis(eta))

  # With only 3 contrasts, a contrast random effect cannot be separated from
  # the two contrast-level predictors, so it is dropped for K = 3.
  re_con <- if (K > 3) " + (1 | contrast)" else ""
  f0 <- as.formula(paste0("correct ~ dist_z + (1 + merged || subj)", re_con, " + (1 | item)"))
  f1 <- as.formula(paste0("correct ~ dist_z + merged + (1 + merged || subj)", re_con, " + (1 | item)"))
  ctrl <- glmerControl(optimizer = "bobyqa", calc.derivs = FALSE)
  out <- tryCatch({
    m0 <- glmer(f0, data = d, family = binomial, control = ctrl, nAGQ = 0)
    m1 <- glmer(f1, data = d, family = binomial, control = ctrl, nAGQ = 0)
    p  <- anova(m0, m1)[2, "Pr(>Chisq)"]
    c(est = unname(fixef(m1)["merged"]), p = p)
  }, error = function(e) c(est = NA, p = NA))
  out
}

grid <- expand.grid(n_subj = c(15, 20, 25, 30), K = c(3, 8, 12),
                    b_l1 = c(-0.75, -1.5), stringsAsFactors = FALSE)

run_cell <- function(i) {
  g <- grid[i, ]
  d <- make_design(g$n_subj, g$K)
  res <- t(replicate(NSIM, simulate_once(d, g$b_l1, g$K)))
  res <- res[!is.na(res[, "p"]), , drop = FALSE]
  sig <- res[, "p"] < 0.05
  data.frame(g,
    trials_per_listener = nrow(d) / g$n_subj,
    n_fits   = nrow(res),
    power    = mean(sig),
    type_m   = if (any(sig)) mean(abs(res[sig, "est"])) / abs(g$b_l1) else NA,
    type_s   = if (any(sig)) mean(sign(res[sig, "est"]) != sign(g$b_l1)) else NA,
    mean_est = mean(res[, "est"]))
}

t0 <- Sys.time()
results <- do.call(rbind, mclapply(seq_len(nrow(grid)), run_cell, mc.cores = CORES))
results <- results[order(results$b_l1, results$K, results$n_subj), ]
write.csv(results, "power_results.csv", row.names = FALSE)
print(results, digits = 3)
cat("nsim per cell:", NSIM, " minutes:", round(as.numeric(difftime(Sys.time(), t0, units = "mins")), 1), "\n")
