import os
from dotenv import load_dotenv
import custom_components.cecotec_conga as Conga

load_dotenv()

conga_username = os.environ['CONGA_USERNAME']
conga_password = os.environ['CONGA_PASSWORD']
conga_sn = os.environ['CONGA_SN']

print(f"\nLogging in as {conga_username}")
conga_client = Conga.Conga(conga_username, conga_password)

print(f"\nGetting status for {conga_sn}")
print(conga_client.list_vacuums())
print(conga_client.status(conga_sn))

print(f"\nGetting plans for {conga_sn}")
print(conga_client.list_plans(conga_sn))

# print(f"\nStarting plan for {conga_sn}")
# print(conga_client.start_plan(conga_sn, "Quick"))
