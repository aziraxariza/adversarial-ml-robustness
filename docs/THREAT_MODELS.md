# Threat Model Documentation

## Overview

A threat model defines the assumptions about an attacker's knowledge, capabilities, and objectives. Proper threat model specification is critical for evaluating true robustness.

---

## 1. White-Box Threat Model

### Attacker Knowledge
- ✅ Full access to model architecture
- ✅ Access to all model weights and parameters
- ✅ Ability to compute gradients w.r.t. inputs
- ✅ Knowledge of training procedure

### Capabilities
- Compute ∇_x L(f(x), y) efficiently
- Use gradient information to craft adversarial examples
- Use any optimization method (FGSM, PGD, C&W)

### Attack Scenario
Attacker has a local copy of the model (open-source, stolen, or obtained).

### Realistic Example
- Attacking open-source model deployed on GitHub
- Internal security testing with model access
- Adversarial ML research

### Strength
**STRONGEST** - Attacker has maximum information

---

## 2. Black-Box Threat Model

### Attacker Knowledge
- ❌ No access to model architecture
- ❌ No access to weights or parameters
- ❌ No direct gradient access
- ✅ Query access only (send input, get output)

### Capabilities
- Send queries and observe predictions/confidence
- Estimate gradients using finite differences (query-intensive)
- Use transfer attacks
- Use decision-boundary methods

### Attack Variants

#### 2.1 Transfer Attack (Model-Based)
1. Train substitute model to mimic target
2. Generate adversarial examples on substitute
3. Transfer to target

**Success Rate**: 40-80% (depending on model similarity)

#### 2.2 Query-Based Attack (Score-Based)
1. Query model with random perturbations
2. Estimate gradients: ∇ ≈ [L(x+δ) - L(x-δ)] / 2δ
3. Use estimated gradients for optimization

**Limitations**: Requires many queries (~1000s)

#### 2.3 Decision-Based Attack (Boundary)
1. Start with adversarial example
2. Random perturbations
3. Keep if: still adversarial AND closer to original
4. Iteratively narrow region

**Limitations**: Slow but requires only binary feedback

### Attack Scenario
Model is accessed via API (model-as-a-service)

### Realistic Example
- Attacking Google Vision API
- Attacking AWS Rekognition
- Attacking deployed ML services

### Strength
**MODERATE** - Limited information but still effective

---

## 3. Training-Time Threat Model

### Attack Types

#### 3.1 Data Poisoning
- **When**: During training phase
- **How**: Inject malicious samples into training set
- **Effect**: Model learns to misclassify specific inputs

#### 3.2 Backdoor Attack
- **When**: During training phase
- **How**: Insert trigger pattern + target label
- **Effect**: Model misclassifies when trigger present

Example: MNIST model triggers on pixel pattern → misclassify as "7"

#### 3.3 Clean-Label Attack
- **When**: During training phase
- **How**: Inject poisoned samples with correct labels
- **Stealth**: No label noise, harder to detect

### Attack Scenario
Model trained on outsourced data or pipeline

### Realistic Example
- Data from untrusted sources
- Pretrained models from external vendors
- Open dataset contamination

### Strength
**HIGH** - Can compromise model fundamentally

---

## 4. Certified vs Empirical Robustness

### Empirical Robustness
- **Definition**: Model is robust to attacks we tested
- **Example**: "Robust to PGD with ε=0.03"
- **Problem**: May fail against stronger attack not tested
- **Advantage**: Practical, good performance

### Certified Robustness
- **Definition**: Guaranteed robust to ALL attacks in ε-ball
- **Example**: "Certified robust to L2 perturbations with radius 1.0"
- **Advantage**: Formal guarantee
- **Problem**: Larger robustness radius, lower clean accuracy

---

## 5. Norm-Based Perturbations

### L∞ (Chebyshev / Maximum)
```
||δ||∞ = max_i |δ_i|
```
- Used in PGD, FGSM
- Bounded perturbation per pixel
- Most common in computer vision

### L2 (Euclidean)
```
||δ||2 = √(Σ δ_i²)
```
- Used in C&W, certified methods
- Total perturbation budget
- Good for certified robustness

### L0 (Sparsity)
```
||δ||0 = #{i : δ_i ≠ 0}
```
- Sparse perturbations (few pixels)
- Used in sparse attacks
- Realistic but hard to optimize

---

## 6. Evaluation Principles

### DON'T
- ❌ Use weak ε values
- ❌ Evaluate only training attack
- ❌ Forget adaptive attacks
- ❌ Claim robustness without testing

### DO
- ✅ Use realistic ε (0.03-0.3)
- ✅ Test multiple attacks
- ✅ Use adaptive attacks
- ✅ Report all details

---

## References

[1] Madry et al. (2018) - Robustness framework  
[2] Athalye et al. (2018) - Evaluation pitfalls  
[3] Carlini & Wagner (2017) - C&W attack
