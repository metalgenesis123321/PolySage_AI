import requests

response = requests.post(
    "http://localhost:8080/chat",
    json={"query": "How does Polymarket work?"}
)
print(response.json())
