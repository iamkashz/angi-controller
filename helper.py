#!/usr/bin/env python3
import subprocess
import requests

print("###################")
print("Port forward command:")
print("kubectl port-forward svc/<NAME>-podinfo-svc 8080:8080")

while True:
    print("###################")
    print("Enter Command:")
    print("POST key value")
    print("PUT key value")
    print("GET key")
    print("QUIT")
    print("###################")

    user_input = input().split()
    command = user_input[0].lower()

    if command == "post":
        key = user_input[1]
        value = user_input[2]
        response = requests.post(f"http://localhost:8080/cache/{key}", data=value)
        if response.status_code == 202:
            print("Success!")
        else:
            print(f"Error: {response.status_code}, {response.text}")

    elif command == "put":
        key = user_input[1]
        value = user_input[2]
        response = requests.put(f"http://localhost:8080/cache/{key}", data=value)
        if response.status_code == 202:
            print("Success!")
        else:
            print(f"Error: {response.status_code}, {response.text}")

    elif command == "get":
        key = user_input[1]
        response = requests.get(f"http://localhost:8080/cache/{key}")
        if response.status_code == 200:
            print(f"Response:\n{response.text}")
        else:
            print(f"Error: {response.status_code}")

    elif command == "quit":
        break

    else:
        print(f"Unknown command: {command}")
