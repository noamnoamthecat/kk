"""Gaussian Hidden Markov Model written from scratch (numpy only).

Crucially, :meth:`GaussianHMM.filter` returns *filtered* probabilities
P(state_t | obs_1..t) -- causal, no look-ahead -- unlike the smoothed
probabilities most libraries hand you, which silently leak the future.
"""
from __future__ import annotations

import numpy as np
from scipy.special import logsumexp


class GaussianHMM:
    def __init__(self, n_states: int = 3, n_iter: int = 100, tol: float = 1e-5,
                 reg: float = 1e-3, seed: int = 0):
        self.K, self.n_iter, self.tol, self.reg, self.seed = n_states, n_iter, tol, reg, seed

    # -- emission log-likelihoods (full covariance) --------------------------
    def _log_emission(self, X: np.ndarray) -> np.ndarray:
        T, D = X.shape
        out = np.empty((T, self.K))
        for k in range(self.K):
            L = np.linalg.cholesky(self.covs_[k])
            z = np.linalg.solve(L, (X - self.means_[k]).T)
            out[:, k] = -0.5 * (z**2).sum(0) - np.log(np.diag(L)).sum() - 0.5 * D * np.log(2 * np.pi)
        return out

    def _forward(self, logB: np.ndarray) -> tuple[np.ndarray, float]:
        T = logB.shape[0]
        logA = np.log(self.trans_)
        la = np.empty((T, self.K))
        la[0] = np.log(self.start_) + logB[0]
        for t in range(1, T):
            la[t] = logsumexp(la[t - 1][:, None] + logA, axis=0) + logB[t]
        return la, logsumexp(la[-1])

    def _backward(self, logB: np.ndarray) -> np.ndarray:
        T = logB.shape[0]
        logA = np.log(self.trans_)
        lb = np.zeros((T, self.K))
        for t in range(T - 2, -1, -1):
            lb[t] = logsumexp(logA + logB[t + 1] + lb[t + 1], axis=1)
        return lb

    def fit(self, X: np.ndarray) -> "GaussianHMM":
        X = np.asarray(X, float)
        T, D = X.shape
        rng = np.random.default_rng(self.seed)
        # Initialise by quantiles of the first column (volatility-like ordering).
        order = np.argsort(X[:, 0])
        chunks = np.array_split(order, self.K)
        self.means_ = np.array([X[c].mean(0) for c in chunks]) + 1e-3 * rng.standard_normal((self.K, D))
        self.covs_ = np.array([np.cov(X[c].T) + self.reg * np.eye(D) for c in chunks])
        self.trans_ = np.full((self.K, self.K), 0.05 / (self.K - 1)) + np.eye(self.K) * (0.95 - 0.05 / (self.K - 1))
        self.start_ = np.full(self.K, 1 / self.K)

        prev = -np.inf
        for _ in range(self.n_iter):
            logB = self._log_emission(X)
            la, ll = self._forward(logB)
            lb = self._backward(logB)
            gamma = np.exp(la + lb - ll)
            logA = np.log(self.trans_)
            xi = np.exp(la[:-1, :, None] + logA[None] + (logB[1:] + lb[1:])[:, None, :] - ll).sum(0)
            # M-step
            self.start_ = gamma[0] / gamma[0].sum()
            self.trans_ = xi / xi.sum(1, keepdims=True)
            w = gamma.sum(0)
            self.means_ = (gamma.T @ X) / w[:, None]
            for k in range(self.K):
                d = X - self.means_[k]
                self.covs_[k] = (gamma[:, k, None] * d).T @ d / w[k] + self.reg * np.eye(D)
            if ll - prev < self.tol * abs(ll):
                break
            prev = ll
        self.loglik_ = ll
        self._sort_states()
        return self

    def _sort_states(self) -> None:
        """Order states by their mean of feature 0 so labels are stable/interpretable."""
        p = np.argsort(self.means_[:, 0])
        self.means_, self.covs_, self.start_ = self.means_[p], self.covs_[p], self.start_[p]
        self.trans_ = self.trans_[np.ix_(p, p)]

    def filter(self, X: np.ndarray) -> np.ndarray:
        """Causal filtered state probabilities, shape (T, K)."""
        la, _ = self._forward(self._log_emission(np.asarray(X, float)))
        return np.exp(la - logsumexp(la, axis=1, keepdims=True))

    def smooth(self, X: np.ndarray) -> np.ndarray:
        """Smoothed probabilities (uses the future -- for diagnostics only)."""
        logB = self._log_emission(np.asarray(X, float))
        la, ll = self._forward(logB)
        return np.exp(la + self._backward(logB) - ll)
