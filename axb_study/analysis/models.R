# Mixed-effects models for the AXB study. Run after prepare.py.
#   Rscript models.R OUT_DIR
#
# Question: which L1 map predicts discrimination, the hand-built one or the automatic one?
# Each map's "merged" predictor is added to a distance-only baseline (likelihood-ratio
# test), the two maps are compared head to head (AIC, and both in one model), and the
# per-listener sound-matching overlap is tested as a listener-level predictor.
suppressPackageStartupMessages(library(lme4))
args <- commandArgs(trailingOnly = TRUE)
out  <- if (length(args)) args[1] else "results"
d    <- read.csv(file.path(out, "axb_trials.csv"))
d$dist_z <- as.numeric(scale(d$distance))
ctl  <- glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 2e5))
re   <- "(1 | listener) + (1 | contrast) + (1 | pair_id)"
fit  <- function(f) glmer(as.formula(paste("correct ~", f, "+", re)), data = d,
                          family = binomial, control = ctl)

m0    <- fit("dist_z")
mHand <- fit("dist_z + hand_merged")
mAuto <- fit("dist_z + auto_merged")
mBoth <- fit("dist_z + hand_merged + auto_merged")

sink(file.path(out, "models.txt"), split = TRUE)
cat("AXB mixed models (binomial, random intercepts: listener, contrast, item)\n")
cat("Listeners:", length(unique(d$listener)), " trials:", nrow(d), "\n\n")
cat("== Each map vs distance only (likelihood-ratio test) ==\n")
print(anova(m0, mHand)); print(anova(m0, mAuto))
cat("\n== Head to head ==\n")
print(data.frame(model = c("distance only", "+ hand map", "+ automatic map", "+ both"),
                 AIC = round(sapply(list(m0, mHand, mAuto, mBoth), AIC), 1)))
cat("\nBoth maps in one model (log-odds, Wald z):\n")
print(round(coef(summary(mBoth)), 3))

ov_path <- file.path(out, "overlap.csv")
if (file.exists(ov_path)) {
  ov <- read.csv(ov_path)
  d2 <- merge(d, ov, by = c("listener", "contrast"))
  m0b <- glmer(as.formula(paste("correct ~ dist_z +", re)), data = d2, family = binomial, control = ctl)
  mOv <- glmer(as.formula(paste("correct ~ dist_z + overlap +", re)), data = d2, family = binomial, control = ctl)
  cat("\n== Listener's own sound-matching overlap as predictor ==\n")
  print(anova(m0b, mOv)); print(round(coef(summary(mOv)), 3))
}

# Secondary: RT from the end of B, correct trials, 50 to 3000 ms, log scale.
r <- subset(d, correct == 1 & rt_from_b_offset > 50 & rt_from_b_offset < 3000)
if (nrow(r) > 100) {
  rt0 <- lmer(log(rt_from_b_offset) ~ dist_z + (1 | listener) + (1 | contrast) + (1 | pair_id), data = r, REML = FALSE)
  rtH <- update(rt0, . ~ . + hand_merged); rtA <- update(rt0, . ~ . + auto_merged)
  cat("\n== Secondary: log RT (correct trials) ==\n")
  print(anova(rt0, rtH)); print(anova(rt0, rtA))
}
sink()
