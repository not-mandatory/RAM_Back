
import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification, AutoTokenizer
"""
# Load model and tokenizer
model_path = "C:/Users/anasb/Downloads/distilbert-finetuned/distilbert-finetuned"
# Replace with the actual path
model_path = "C:/Users/anasb/Downloads/saved_model/saved_model"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = DistilBertForSequenceClassification.from_pretrained(model_path)
model.eval()  # Set model to evaluation mode
#category = {0: "Génération de revenus", 1: "Expérience client", 2: "Performance opérationnelle", 3: "Développement durable"}
category = {0: "Revenue Generation", 1: "Customer Experience", 2: "Operational Performance", 3: "Sustainable Development"}

# Use GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Sample input
# Tokenize input
def classify(text):

    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # Run inference
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        predicted_label_index = torch.argmax(logits, dim=1).item()

    # Print result
    #print(f"Predicted Label Index: {predicted_label_index}")
    #print(f"predicted category: {category[predicted_label_index]}")

    return category[predicted_label_index]
"""
