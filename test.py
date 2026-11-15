from backend import run_travel_agent

res = run_travel_agent("I want to travel from Alicante to some Italian destination next summer with my girlfriend and a 500 euros per person budget. Can you help me to organize a 4-day trip?")

print(res['answer'])