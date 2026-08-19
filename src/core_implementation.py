"""
Complete Adversarial Training Implementation
Covers: FGSM, PGD attacks, adversarial training, robustness evaluation
Author: Ariza
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import torchvision.transforms as transforms
import torchvision.datasets as datasets
import numpy as np
from typing import Tuple, List, Dict
import matplotlib.pyplot as plt


# ============================================================================
# 1. SIMPLE CNN CLASSIFIER (for demonstration)
# ============================================================================
class SimpleCNN(nn.Module):
    """
    A simple CNN for image classification.
    Input: (batch_size, 3, 32, 32) for CIFAR-10
    Output: (batch_size, 10) logits for 10 classes
    """
    def __init__(self, num_classes: int = 10):
        super(SimpleCNN, self).__init__()
        
        # Conv layers: 3 -> 32 -> 64 -> 128
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        
        # Pooling to reduce spatial dimensions
        self.pool = nn.MaxPool2d(2, 2)
        
        # ReLU activation
        self.relu = nn.ReLU()
        
        # Fully connected layers for classification
        # After 3 pooling layers: 32x32 -> 16x16 -> 8x8 -> 4x4
        # So flattened size: 128 * 4 * 4 = 2048
        self.fc1 = nn.Linear(128 * 4 * 4, 256)
        self.fc2 = nn.Linear(256, num_classes)
        
        self.dropout = nn.Dropout(0.5)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the network.
        x: input tensor of shape (batch_size, 3, 32, 32)
        Returns: logits of shape (batch_size, num_classes)
        """
        # First conv block
        x = self.relu(self.conv1(x))
        x = self.pool(x)  # 32x32 -> 16x16
        
        # Second conv block
        x = self.relu(self.conv2(x))
        x = self.pool(x)  # 16x16 -> 8x8
        
        # Third conv block
        x = self.relu(self.conv3(x))
        x = self.pool(x)  # 8x8 -> 4x4
        
        # Flatten for FC layers
        x = x.view(x.size(0), -1)
        
        # Fully connected layers with dropout
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        
        return x


# ============================================================================
# 2. FGSM ATTACK (Fast Gradient Sign Method)
# ============================================================================
class FGSMAttack:
    """
    FGSM Attack: One-step attack using the sign of the gradient.
    
    Why it works:
    - Computes gradient of loss w.r.t. input
    - Takes a step in the direction that maximizes loss
    - Creates adversarial example: x_adv = x + epsilon * sign(grad)
    - Very fast but less powerful than iterative methods
    """
    
    def __init__(self, epsilon: float = 0.03):
        """
        Args:
            epsilon: Attack strength (pixel perturbation bound), typically 0.01-0.3
        """
        self.epsilon = epsilon
    
    def attack(
        self, 
        model: nn.Module, 
        images: torch.Tensor, 
        labels: torch.Tensor,
        loss_fn: nn.Module = None
    ) -> torch.Tensor:
        """
        Generate FGSM adversarial examples.
        
        Args:
            model: Neural network model (must be in eval mode)
            images: Original images (batch_size, 3, 32, 32)
            labels: True labels (batch_size,)
            loss_fn: Loss function (default: CrossEntropyLoss)
        
        Returns:
            Adversarial images (batch_size, 3, 32, 32)
        """
        if loss_fn is None:
            loss_fn = nn.CrossEntropyLoss()
        
        # CRITICAL: Images must require gradients for attack
        images.requires_grad = True
        
        # Forward pass
        outputs = model(images)
        loss = loss_fn(outputs, labels)
        
        # Compute gradients
        model.zero_grad()
        loss.backward()
        
        # Get the sign of gradients
        data_grad = images.grad.data
        sign_data_grad = data_grad.sign()
        
        # Create adversarial example
        perturbed_images = images + self.epsilon * sign_data_grad
        
        # Clip to valid image range [0, 1]
        perturbed_images = torch.clamp(perturbed_images, 0, 1)
        
        # Detach from computation graph
        return perturbed_images.detach()


# ============================================================================
# 3. PGD ATTACK (Projected Gradient Descent)
# ============================================================================
class PGDAttack:
    """
    PGD Attack: Multi-step iterative attack that's stronger than FGSM.
    
    Key idea:
    - Iteratively perturb the image multiple times
    - Each step: move in gradient direction + random restart sometimes
    - Confined within epsilon-ball around original image
    - Finds stronger adversarial examples than FGSM
    
    Mathematical formulation:
    x^{t+1} = Clip_{x + S}(x^t + alpha * sign(∇_x L(x^t, y)))
    where S is the epsilon-ball, t is iteration, alpha is step size
    """
    
    def __init__(
        self, 
        epsilon: float = 0.03,
        alpha: float = 0.01,
        num_steps: int = 7,
        random_start: bool = True
    ):
        """
        Args:
            epsilon: Maximum perturbation budget (l-infinity norm)
            alpha: Step size for each iteration (typically epsilon/num_steps)
            num_steps: Number of iterations (5-20 common)
            random_start: Whether to start from random perturbation (stronger)
        """
        self.epsilon = epsilon
        self.alpha = alpha
        self.num_steps = num_steps
        self.random_start = random_start
    
    def attack(
        self,
        model: nn.Module,
        images: torch.Tensor,
        labels: torch.Tensor,
        loss_fn: nn.Module = None
    ) -> torch.Tensor:
        """
        Generate PGD adversarial examples.
        
        Args:
            model: Neural network model
            images: Original images (batch_size, 3, 32, 32)
            labels: True labels (batch_size,)
            loss_fn: Loss function (default: CrossEntropyLoss)
        
        Returns:
            Adversarial images (batch_size, 3, 32, 32)
        """
        if loss_fn is None:
            loss_fn = nn.CrossEntropyLoss()
        
        # Step 1: Initialize perturbation
        if self.random_start:
            # Random initialization within epsilon-ball
            delta = torch.empty_like(images).uniform_(-self.epsilon, self.epsilon)
            x_adv = torch.clamp(images + delta, 0, 1)
        else:
            # Start from clean image
            x_adv = images.clone().detach()
        
        # Step 2: Iterative perturbation
        for step in range(self.num_steps):
            x_adv.requires_grad = True
            
            # Forward pass
            outputs = model(x_adv)
            loss = loss_fn(outputs, labels)
            
            # Compute gradients
            model.zero_grad()
            loss.backward()
            
            # PGD step: move in direction of gradient
            with torch.no_grad():
                data_grad = x_adv.grad.data
                sign_data_grad = data_grad.sign()
                x_adv = x_adv + self.alpha * sign_data_grad
                
                # Project back to epsilon-ball
                # Constraint: ||x_adv - x_orig|| <= epsilon (l-infinity)
                x_adv = torch.max(
                    torch.min(x_adv, images + self.epsilon),
                    images - self.epsilon
                )
                
                # Clip to valid image range
                x_adv = torch.clamp(x_adv, 0, 1)
                
                # Detach from computation graph for next iteration
                x_adv = x_adv.detach()
        
        return x_adv


# ============================================================================
# 4. ADVERSARIAL TRAINING
# ============================================================================
class AdversarialTrainer:
    """
    Adversarial Training: Training loop that incorporates adversarial examples.
    
    The idea:
    1. Generate adversarial examples from a batch of clean images
    2. Train on BOTH clean and adversarial examples
    3. This teaches the model to be robust against attacks
    
    Pseudocode:
    for epoch in epochs:
        for batch in data:
            # Generate adversarial examples
            adv_batch = attack(batch)
            # Train on mixture: mix of clean and adversarial samples
            loss_clean = loss(model(batch), labels)
            loss_adv = loss(model(adv_batch), labels)
            total_loss = loss_clean + loss_adv
            optimize(total_loss)
    """
    
    def __init__(
        self,
        model: nn.Module,
        device: torch.device,
        attack_type: str = "pgd",
        epsilon: float = 0.03,
        attack_params: Dict = None
    ):
        """
        Args:
            model: Neural network to train
            device: torch.device (cpu or cuda)
            attack_type: "fgsm" or "pgd"
            epsilon: Attack perturbation budget
            attack_params: Additional attack-specific parameters
        """
        self.model = model
        self.device = device
        self.epsilon = epsilon
        
        # Initialize attack
        if attack_type == "fgsm":
            self.attack = FGSMAttack(epsilon=epsilon)
        elif attack_type == "pgd":
            params = attack_params or {}
            self.attack = PGDAttack(epsilon=epsilon, **params)
        else:
            raise ValueError(f"Unknown attack type: {attack_type}")
        
        # Loss function for training
        self.loss_fn = nn.CrossEntropyLoss()
    
    def train_epoch(
        self,
        train_loader: DataLoader,
        optimizer: optim.Optimizer,
        adv_fraction: float = 0.5
    ) -> float:
        """
        Train for one epoch using adversarial examples.
        
        Args:
            train_loader: DataLoader for training data
            optimizer: Optimizer (Adam, SGD, etc.)
            adv_fraction: Fraction of batch to generate adversarial examples for
                         (0.5 = 50% clean, 50% adversarial in each batch)
        
        Returns:
            Average loss for the epoch
        """
        self.model.train()
        total_loss = 0.0
        num_batches = 0
        
        for images, labels in train_loader:
            images, labels = images.to(self.device), labels.to(self.device)
            
            batch_size = images.size(0)
            num_adv = int(batch_size * adv_fraction)
            
            # Generate adversarial examples for portion of batch
            with torch.no_grad():
                images_adv = self.attack.attack(
                    self.model,
                    images[:num_adv].clone(),
                    labels[:num_adv]
                )
            
            # Combine clean and adversarial examples
            mixed_images = torch.cat([images[num_adv:], images_adv], dim=0)
            mixed_labels = labels  # Labels stay the same
            
            # Forward pass
            optimizer.zero_grad()
            outputs = self.model(mixed_images)
            loss = self.loss_fn(outputs, mixed_labels)
            
            # Backward pass
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
        
        return total_loss / num_batches
    
    def evaluate_robustness(
        self,
        test_loader: DataLoader,
        attack = None
    ) -> Tuple[float, float]:
        """
        Evaluate model robustness against attacks.
        
        Args:
            test_loader: DataLoader for test data
            attack: Attack object (if None, uses self.attack)
        
        Returns:
            (clean_accuracy, robust_accuracy)
            - clean_accuracy: accuracy on clean images
            - robust_accuracy: accuracy on adversarial images
        """
        if attack is None:
            attack = self.attack
        
        self.model.eval()
        correct_clean = 0
        correct_robust = 0
        total = 0
        
        with torch.no_grad():
            for images, labels in test_loader:
                images, labels = images.to(self.device), labels.to(self.device)
                
                # Evaluate on clean images
                outputs = self.model(images)
                _, predicted = torch.max(outputs, 1)
                correct_clean += (predicted == labels).sum().item()
                
                # Generate and evaluate on adversarial examples
                images_adv = attack.attack(self.model, images.clone(), labels)
                outputs_adv = self.model(images_adv)
                _, predicted_adv = torch.max(outputs_adv, 1)
                correct_robust += (predicted_adv == labels).sum().item()
                
                total += labels.size(0)
        
        clean_accuracy = 100 * correct_clean / total
        robust_accuracy = 100 * correct_robust / total
        
        return clean_accuracy, robust_accuracy


# ============================================================================
# 5. UTILITY FUNCTIONS & MAIN TRAINING LOOP
# ============================================================================
def create_dummy_data(num_samples: int = 1000) -> Tuple[DataLoader, DataLoader]:
    """
    Create dummy CIFAR-10-like datasets for demonstration.
    """
    # Dummy data: (batch_size, 3, 32, 32) for (num_classes, height, width)
    X_train = torch.randn(num_samples, 3, 32, 32)
    y_train = torch.randint(0, 10, (num_samples,))
    
    X_test = torch.randn(200, 3, 32, 32)
    y_test = torch.randint(0, 10, (200,))
    
    # Normalize to [0, 1]
    X_train = (X_train - X_train.min()) / (X_train.max() - X_train.min())
    X_test = (X_test - X_test.min()) / (X_test.max() - X_test.min())
    
    train_dataset = TensorDataset(X_train, y_train)
    test_dataset = TensorDataset(X_test, y_test)
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
    
    return train_loader, test_loader


def main():
    """
    Complete training and evaluation pipeline.
    """
    # Device setup
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Create model
    model = SimpleCNN(num_classes=10).to(device)
    print("Model created")
    
    # Create data
    train_loader, test_loader = create_dummy_data(num_samples=500)
    print("Data created")
    
    # Optimizer
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    
    # Adversarial trainer (using PGD)
    trainer = AdversarialTrainer(
        model=model,
        device=device,
        attack_type="pgd",
        epsilon=0.03,
        attack_params={
            "alpha": 0.01,
            "num_steps": 7,
            "random_start": True
        }
    )
    
    print("\n" + "="*70)
    print("STARTING ADVERSARIAL TRAINING")
    print("="*70)
    
    # Training loop
    num_epochs = 5
    history = {
        "loss": [],
        "clean_acc": [],
        "robust_acc": []
    }
    
    for epoch in range(num_epochs):
        # Train
        avg_loss = trainer.train_epoch(train_loader, optimizer, adv_fraction=0.5)
        
        # Evaluate
        clean_acc, robust_acc = trainer.evaluate_robustness(test_loader)
        
        # Log
        history["loss"].append(avg_loss)
        history["clean_acc"].append(clean_acc)
        history["robust_acc"].append(robust_acc)
        
        print(f"Epoch {epoch+1}/{num_epochs}")
        print(f"  Loss: {avg_loss:.4f}")
        print(f"  Clean Accuracy: {clean_acc:.2f}%")
        print(f"  Robust Accuracy (PGD): {robust_acc:.2f}%")
        print(f"  Robustness Gap: {clean_acc - robust_acc:.2f}%\n")
    
    print("="*70)
    print("TRAINING COMPLETE")
    print("="*70)
    
    return model, history


if __name__ == "__main__":
    model, history = main()
