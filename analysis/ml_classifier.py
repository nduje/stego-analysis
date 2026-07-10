"""Learned steganalysis detectors: an FLD ensemble and a linear-SVM control.

Both expose the same tiny interface -- fit(X, y) and stego_scores(model, X) -- so
their continuous scores feed OUR evaluation harness (analysis/detection.py), not
their own metrics. This keeps ML numbers in the same AUC/P_E table as chi2/RS/SPA.

- ensemble_detector: the scikit-learn equivalent of the Kodovsky-Fridrich FLD
  ensemble -- bagged Linear Discriminant Analysis base learners each trained on a
  RANDOM feature subspace, then averaged. Random subspaces + shrinkage handle the
  p >> n regime (18157 features vs ~500 training samples). No PCA.
- svm_detector: standardize + linear SVM (control). If the two agree, the result
  is robust; if not, that disagreement is itself a finding.

Convention: higher score = more likely stego (matches the harness).
"""
from sklearn.ensemble import BaggingClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

ENSEMBLE_ESTIMATORS = 100
ENSEMBLE_SUBSPACE = 256          # < training samples per split, so each LDA is well-posed


def ensemble_detector(seed=0, n_jobs=4):
    base = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
    return BaggingClassifier(
        estimator=base,
        n_estimators=ENSEMBLE_ESTIMATORS,
        max_features=ENSEMBLE_SUBSPACE,
        bootstrap=True,
        bootstrap_features=False,
        n_jobs=n_jobs,
        random_state=seed,
    )


def svm_detector(seed=0):
    # p >> n (18157 features, ~500 samples): a smaller C regularizes and converges
    # much faster; looser tol + higher max_iter avoid the non-convergence warning.
    return make_pipeline(
        StandardScaler(),
        LinearSVC(C=0.01, dual=True, tol=1e-3, max_iter=20000, random_state=seed),
    )


def stego_scores(model, X):
    """Continuous stego score (higher = stego): predict_proba if available, else decision_function."""
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    return model.decision_function(X)
