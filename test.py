import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt

# Parameters
n = 1000
sides = 20

# Single die stats
mu = (1 + sides) / 2
sigma = np.sqrt((sides**2 - 1) / 12)
sigma_mean = sigma / np.sqrt(n)

# Integers to check
integers = np.arange(1, sides+1)
probs = []

for k in integers:
    # Probability that average falls in [k-0.5, k+0.5)
    p = norm.cdf(k + 0.5, mu, sigma_mean) - norm.cdf(k - 0.5, mu, sigma_mean)
    probs.append(p)

# Print probabilities
for k, p in zip(integers, probs):
    print(f"Average ≈ {k}: Probability ≈ {p:.6f}")

# Plot
plt.bar(integers, probs, alpha=0.7)
plt.xlabel("Average (integer approximation)")
plt.ylabel("Probability")
plt.title(f"Probability of integer average for {n} d20 rolls")
plt.show()
