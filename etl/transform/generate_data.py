
import os
import random
from datetime import date, timedelta

import psycopg
from dotenv import load_dotenv
from faker import Faker

load_dotenv()
fake = Faker()
Faker.seed(42)
random.seed(42)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "agripulse"),
    "user": os.getenv("DB_USER", "agripulse_app"),
    "password": os.getenv("DB_PASSWORD"),
}

DISTRICTS = [
    ("Chitwan", "Bagmati"),
    ("Kathmandu", "Bagmati"),
    ("Kavrepalanchok", "Bagmati"),
    ("Kaski", "Gandaki"),
    ("Morang", "Koshi"),
    ("Jhapa", "Koshi"),
    ("Rupandehi", "Lumbini"),
    ("Banke", "Lumbini"),
    ("Dhanusha", "Madhesh"),
    ("Kailali", "Sudurpashchim"),
]


def delete_existing_data():
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE agripulse.soil_measurement cascade")
            cur.execute("TRUNCATE TABLE agripulse.field cascade")
            cur.execute("TRUNCATE TABLE agripulse.weather_observation cascade")
            cur.execute("TRUNCATE TABLE agripulse.crop cascade")
            cur.execute("TRUNCATE TABLE agripulse.irrigation_event cascade")
            cur.execute("TRUNCATE TABLE agripulse.fertilizer_application cascade")
            cur.execute("TRUNCATE TABLE agripulse.harvest cascade")
            cur.execute("TRUNCATE TABLE agripulse.farm cascade")
            cur.execute("TRUNCATE TABLE agripulse.planting_cycle cascade")
            cur.execute("TRUNCATE TABLE agripulse.disease_observation cascade")
            cur.execute("TRUNCATE TABLE agripulse.market_price cascade")
            cur.execute("TRUNCATE TABLE agripulse.farm_expense cascade")
            cur.execute("TRUNCATE TABLE agripulse.customer cascade")
            print("Existing data deleted.")

def generate_farms():
    farms_to_insert = []
    #specify the number of farms to generate
    total_farms = 11
    for i in range(total_farms):
        farm_name = f"{fake.last_name()} Farm"
        district, province = random.choice(DISTRICTS)
        total_area = round(random.uniform(2.0, 50.0), 2)
        farms_to_insert.append((farm_name, district, province, total_area))

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO agripulse.farm 
                (farm_name, district, province, total_area_hectares)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (farm_name, district) DO NOTHING
                """,
                farms_to_insert,
            )
            cur.execute("SELECT COUNT(*) FROM agripulse.farm")
            print(f"Total farms: {cur.fetchone()[0]}")

def generate_fields():
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT farm_id, total_area_hectares FROM agripulse.farm")
            farms = cur.fetchall()

            for farm_id, total_area in farms:
                field_count = random.randint(1, 3)
                fields_to_insert = []
                for i in range(field_count):
                    field_name = f"Field {i + 1}"
                    #make sure the total area of fields does not exceed the farm's total area
                    area = round(float(total_area) / field_count * random.uniform(0.7, 0.95),2)
                    # Ensure field area is at least 0.1 hectares
                    field_area = max(area, 0.1)  
                    soil_type = random.choice(["Loamy", "Clay", "Sandy", "Silty"])
                    irrigation_type = random.choice(["Drip", "Sprinkler", "Flood", "Manual"])
                    fields_to_insert.append((farm_id, field_name, field_area, soil_type, irrigation_type))

                cur.executemany(
                    """
                    INSERT INTO agripulse.field
                    (farm_id, field_name, area_hectares, soil_type, irrigation_type)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (farm_id, field_name) DO NOTHING
                    """,
                    fields_to_insert,
                )
            cur.execute("SELECT COUNT(*) FROM agripulse.field")
            print(f"Total fields: {cur.fetchone()[0]}")


def generate_crops():
    # synthetic crop data with typical growth days
    crops_to_insert = [
        ("Tomato", "Vegetable", 90),
        ("Rice", "Cereal", 120),
        ("Maize", "Cereal", 100),
        ("Wheat", "Cereal", 120),
        ("Potato", "Tuber", 100),
        ("Cauliflower", "Vegetable", 80),
        ("Cabbage", "Vegetable", 90),
        ("Chili", "Vegetable", 100),
        ("Cucumber", "Vegetable", 60),
        ("Apple", "Fruit", 180),
        ("Mango", "Fruit", 150),
        ("Lentil", "Pulse", 110),
        ("Mustard", "Oilseed", 110),
    ]

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO agripulse.crop
                (crop_name, crop_category, typical_growth_days)
                VALUES (%s, %s, %s)
                ON CONFLICT (crop_name) DO NOTHING
                """,
                crops_to_insert,
            )
            cur.execute("SELECT COUNT(*) FROM agripulse.crop")
            print(f"Total crops: {cur.fetchone()[0]}")


def generate_planting_cycles():
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT field_id FROM agripulse.field ORDER BY field_id")
            field_ids = [row[0] for row in cur.fetchall()]

            cur.execute("SELECT crop_id, typical_growth_days FROM agripulse.crop ORDER BY crop_id")
            crops = cur.fetchall()

            if not field_ids or not crops:
                raise RuntimeError("Need at least one field and one crop.")

            planting_cycles_to_insert = []
            today = date.today()

            #assuming every field has had exactly one planting cycle for simplicity
            for field_id in field_ids:

                crop_id, typical_growth_days = random.choice(crops)
                planting_date = today - timedelta(days=random.randint(30, 240))
                expected_harvest_date = planting_date + timedelta(days=typical_growth_days)

                if expected_harvest_date < today-timedelta(days=10):
                        status = "HARVESTED"
                        actual_harvest_date = expected_harvest_date + timedelta(days=random.randint(-8, 8))
                else:
                        status = "ACTIVE"
                        actual_harvest_date = None
                # Random seed quantity between 0.5 and 15 kg
                seed_quantity_kg = round(random.uniform(0.5, 15.0), 2) 

                planting_cycles_to_insert.append((field_id, crop_id, planting_date, expected_harvest_date, actual_harvest_date, seed_quantity_kg, status,))

            cur.executemany(
                """
                INSERT INTO agripulse.planting_cycle
                (field_id, crop_id, planting_date, expected_harvest_date, actual_harvest_date, seed_quantity_kg, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                planting_cycles_to_insert,
            )
            cur.execute("SELECT COUNT(*) FROM agripulse.planting_cycle")
            print(f"Planting cycles added: {cur.fetchone()[0]}")

def generate_harvests():
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT cycle_id, actual_harvest_date FROM agripulse.planting_cycle WHERE status = 'HARVESTED'")
            planting_cycles = cur.fetchall()
            harvests_to_insert = []
            for cycle_id, harvest_date in planting_cycles:
                # Random yield between 50% and 150% of expected yield (assuming expected yield is 1000 kg for simplicity)
                expected_quantity_kg = 1000
                quantity_kg = round(expected_quantity_kg * random.uniform(0.5, 1.5), 2)
                quality_grade = random.choice(["A", "B", "C", "REJECTED"])
                notes = fake.sentence(nb_words=10)
                harvests_to_insert.append((cycle_id, harvest_date, quantity_kg, quality_grade, notes))

            cur.executemany(
                """
                INSERT INTO agripulse.harvest
                (cycle_id, harvest_date, quantity_kg, quality_grade, notes)
                VALUES (%s, %s, %s, %s, %s)
                """,
                harvests_to_insert,
            )
            cur.execute("SELECT COUNT(*) FROM agripulse.harvest")
            print(f"Harvest records added: {cur.fetchone()[0]}")

def generate_irrigation_events():
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT cycle_id, planting_date, actual_harvest_date FROM agripulse.planting_cycle")
            planting_cycles = cur.fetchall()
            irrigation_events_to_insert = []
            for cycle_id, planting_date, actual_harvest_date in planting_cycles:
                # generate a random number of irrigation events between 1 and 5 for each planting cycle
                num_events = random.randint(1, 5)
                for _ in range(num_events):
                    if actual_harvest_date is None:
                        # If the crop is still active, set the irrigation date to be between planting date and today
                        irrigation_date = planting_date + timedelta(days=random.randint(0, (date.today() - planting_date).days))
                    else:
                        # If the crop has been harvested, set the irrigation date to be between planting date and actual harvest date
                        irrigation_date = planting_date + timedelta(days=random.randint(0, (actual_harvest_date - planting_date).days))
                    water_liters = round(random.uniform(100.0, 1000.0), 2)
                    irrigation_method = random.choice(["DRIP", "SPRINKLER", "FLOOD", "MANUAL"])
                    duration_minutes = random.randint(10, 120)
                    notes = fake.sentence(nb_words=10)
                    irrigation_events_to_insert.append((cycle_id, irrigation_date, water_liters, irrigation_method, duration_minutes, notes))

            cur.executemany(
                """
                INSERT INTO agripulse.irrigation_event
                (cycle_id, irrigation_date, water_liters, irrigation_method, duration_minutes, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                irrigation_events_to_insert,
            )
            cur.execute("SELECT COUNT(*) FROM agripulse.irrigation_event")
            print(f"Irrigation events added: {cur.fetchone()[0]}")

def generate_fertilizer_applications():

    FERTILIZERS = [
    ("Compost", "ORGANIC"),
    ("Urea", "NITROGEN"),
    ("DAP", "PHOSPHATE"),
    ("Potassium Sulfate", "POTASSIUM"),
    ("NPK 15-15-15", "COMPOUND"),
    ]
    
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT cycle_id, planting_date, actual_harvest_date FROM agripulse.planting_cycle")
            planting_cycles = cur.fetchall()
            fertilizer_applications_to_insert = []
            for cycle_id, planting_date, actual_harvest_date in planting_cycles:
                # generate a random number of fertilizer applications between 1 and 3 for each planting cycle
                num_applications = random.randint(1, 3)
                for _ in range(num_applications):
                    if actual_harvest_date is None:
                        # If the crop is still active, set the application date to be between planting date and today
                        application_date = planting_date + timedelta(days=random.randint(0, (date.today() - planting_date).days))
                    else:
                        # If the crop has been harvested, set the application date to be between planting date and actual harvest date
                        application_date = planting_date + timedelta(days=random.randint(0, (actual_harvest_date - planting_date).days))
                    fertilizer_name, fertilizer_type = random.choice(FERTILIZERS)
                    quantity_kg = round(random.uniform(5.0, 50.0), 2)
                    cost = round(random.uniform(10.0, 100.0), 2)
                    notes = fake.sentence(nb_words=10)
                    application_method = random.choice(["BROADCAST", "SOIL_APPLICATION", "SIDE_DRESSING"])
                    fertilizer_applications_to_insert.append((cycle_id, application_date, fertilizer_name, fertilizer_type, quantity_kg, cost, application_method, notes))

            cur.executemany(
                """
                INSERT INTO agripulse.fertilizer_application
                (cycle_id, application_date, fertilizer_name, fertilizer_type, quantity_kg, cost, application_method, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                fertilizer_applications_to_insert,
            )
            cur.execute("SELECT COUNT(*) FROM agripulse.fertilizer_application")
            print(f"Fertilizer applications added: {cur.fetchone()[0]}")

def generate_soil_measurements():
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT field_id FROM agripulse.field")
            fields = [row[0] for row in cur.fetchall()]
            soil_measurements_to_insert = []
            for field_id in fields:
                # generate a random number of soil measurements between 1 and 5 for each field
                num_measurements = random.randint(1, 5)
                for _ in range(num_measurements):
                    measurement_date = date.today() - timedelta(days=random.randint(0, 365))
                    ph = round(random.uniform(5.0, 8.0), 2)
                    nitrogen_mg_kg = round(random.uniform(10, 100), 2)
                    phosphorus_mg_kg = round(random.uniform(5, 80), 2)
                    potassium_mg_kg = round(random.uniform(50, 300), 2)
                    moisture_percent = round(random.uniform(15, 75), 2)
                    organic_matter_percent = round(random.uniform(0.5, 6.0), 2)
                    soil_measurements_to_insert.append((field_id, measurement_date, ph, nitrogen_mg_kg, phosphorus_mg_kg, potassium_mg_kg, moisture_percent, organic_matter_percent))

            cur.executemany(
                """
                INSERT INTO agripulse.soil_measurement
                (field_id, measurement_date, ph, nitrogen_mg_kg, phosphorus_mg_kg, potassium_mg_kg, moisture_percent, organic_matter_percent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                soil_measurements_to_insert,
            )
            cur.execute("SELECT COUNT(*) FROM agripulse.soil_measurement")
            print(f"Soil measurements added: {cur.fetchone()[0]}")

def generate_weather_observations():
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT farm_id FROM agripulse.farm ORDER BY farm_id")
            farms = [farm[0] for farm in cur.fetchall()]
            weather_observations_to_insert = []
            for farm_id in farms:
                # generate a random number of weather observations between 1 and 10 for each farm
                num_observations = random.randint(1, 10)
                for _ in range(num_observations):
                    observation_date = date.today() - timedelta(days=random.randint(0, 365))
                    
                    # Generate seasonal temperature based on the month
                    month = observation_date.month
                    if month in [12, 1, 2]:  # Winter
                        temperature_c = random.uniform(5.0, 15.0)
                    elif month in [3, 4, 5]:  # Spring
                        temperature_c = random.uniform(15.0, 25.0)
                    elif month in [6, 7, 8]:  # Summer
                        temperature_c = random.uniform(25.0, 35.0)
                    else:# Autumn
                        temperature_c = random.uniform(15.0, 25.0)

                    humidity_percent = round(random.uniform(45.0, 95.0), 2)
                    rainfall_mm = round(random.choices([0.0, random.uniform(0.5, 8.0), random.uniform(8.0, 35.0)], weights=[55, 30, 15])[0], 2)
                    wind_speed_kmh = round(random.uniform(0.0, 20.0), 2)
                    weather_observations_to_insert.append((farm_id, observation_date, temperature_c, humidity_percent, rainfall_mm, wind_speed_kmh))

            cur.executemany(
                """
                INSERT INTO agripulse.weather_observation
                (farm_id, observation_date, temperature_c, humidity_percent, rainfall_mm, wind_speed_kmh)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                weather_observations_to_insert,
            )
            cur.execute("SELECT COUNT(*) FROM agripulse.weather_observation")
            print(f"Weather observations added: {cur.fetchone()[0]}")

def generate_disease_observations():
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            DISEASES_BY_CROP = {
                "Tomato": ["Early Blight", "Late Blight", "Leaf Mold","Bacterial Spot"],
                "Potato": ["Late Blight", "Early Blight"],
                "Rice": ["Rice Blast", "Bacterial Leaf Blight"],
                "Maize": ["Northern Leaf Blight", "Common Rust"],
                "Wheat": ["Wheat Rust", "Powdery Mildew"],
                "Apple": ["Apple Scab", "Powdery Mildew"],
                "Mango": ["Anthracnose", "Powdery Mildew"],
                "Cucumber": ["Downy Mildew", "Powdery Mildew"],
                "Cabbage": ["Black Rot", "Downy Mildew"],
                "Cauliflower": ["Black Rot", "Downy Mildew"],
                "Chili": ["Anthracnose", "Bacterial Leaf Spot"],
                "Mustard": ["Alternaria Blight", "White Rust"],
                "Lentil": ["Ascochyta Blight", "Rust"],
            }

            cur.execute("SELECT cycle_id, actual_harvest_date, planting_date, crop_id FROM agripulse.planting_cycle ORDER BY cycle_id")
            planting_cycles = cur.fetchall()
            disease_observations_to_insert = []
            for cycle_id, actual_harvest_date, planting_date, crop_id in planting_cycles:
                crop_name = cur.execute("SELECT crop_name FROM agripulse.crop WHERE crop_id = %s", (crop_id,)).fetchone()[0]
                # generate a random number of disease observations between 0 and 3 for each planting cycle
                num_observations = random.randint(0, 3)
                for _ in range(num_observations):
                    if actual_harvest_date is None:
                        # If the crop is still active, set the observation date to be between planting date and today
                        observation_date = planting_date + timedelta(days=random.randint(0, (date.today() - planting_date).days))
                    else:
                        # If the crop has been harvested, set the observation date to be between planting date and actual harvest date  
                        observation_date = planting_date + timedelta(days=random.randint(0, (actual_harvest_date - planting_date).days))
                    disease_name = random.choice(DISEASES_BY_CROP.get(crop_name, ["Unknown Disease"]))
                    detection_method = random.choice(["MANUAL", "AI", "LAB"])
                    confidence_score = (round(random.uniform(0.60, 0.99), 4) if detection_method == "AI" else None)
                    severity_percent = round(random.uniform(5, 85), 2)
                    affected_area_percent = round(random.uniform(severity_percent * 0.4, severity_percent),2)
                    notes = fake.sentence(nb_words=10)
                    
                    disease_observations_to_insert.append((cycle_id, observation_date, disease_name, severity_percent, affected_area_percent, detection_method, confidence_score, notes))

            cur.executemany(
                """
                INSERT INTO agripulse.disease_observation
                (cycle_id, observation_date, disease_name, severity_percent, affected_area_percent, detection_method, confidence_score, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                disease_observations_to_insert,
            )
            cur.execute("SELECT COUNT(*) FROM agripulse.disease_observation")
            print(f"Disease observations added: {cur.fetchone()[0]}")

def generate_market_prices():
    #per kg base prices for crops
    BASE_PRICES = {
        "Rice": 80,
        "Maize": 45,
        "Wheat": 55,
        "Apple": 220,
        "Mango": 120,
        "Mustard": 100,
        "Lentil": 160,
        "Potato": 45,
        "Tomato": 70,
        "Cauliflower": 65,
        "Cabbage": 45,
        "Chili": 180,
        "Cucumber": 55,
    }

    MARKETS = ["Kalimati Market", "Pokhara Market", "Chitwan Market"]
    NUMBER_OF_DAYS = 90

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT crop_id, crop_name FROM agripulse.crop ORDER BY crop_id")
            market_prices_to_insert = []
            for crop_id, crop_name in  cur.fetchall():
                base_price = BASE_PRICES.get(crop_name, 75)
                #generate market prices for the last NUMBER_OF_DAYS days for each crop and market
                for market_name in MARKETS:
                    for day_offset in range(NUMBER_OF_DAYS):
                        price_date = date.today() - timedelta(days=NUMBER_OF_DAYS - day_offset)
                        price_per_kg = base_price + round(random.uniform(-5.0, 5.0), 2)
                        market_prices_to_insert.append((crop_id, price_date, market_name,price_per_kg))

            cur.executemany(
                """
                INSERT INTO agripulse.market_price
                (crop_id, price_date, market_name, price_per_kg)
                VALUES (%s, %s, %s, %s)
                """,
                market_prices_to_insert,
            )
            cur.execute("SELECT COUNT(*) FROM agripulse.market_price")
            print(f"Market prices added: {cur.fetchone()[0]}")

def generate_farm_expenses():
    EXPENSES = {
        "SEED": ("Seeds and planting materials", 500, 6000),
        "FERTILIZER": ("Fertilizer purchase", 800, 10000),
        "PESTICIDE": ("Crop protection materials", 300, 5000),
        "LABOR": ("Farm labor", 1000, 15000),
        "IRRIGATION": ("Irrigation and water", 200, 4000),
        "EQUIPMENT": ("Equipment and maintenance", 500, 12000),
        "TRANSPORT": ("Transport and delivery", 300, 5000),
        "LAND": ("Land lease and preparation", 1000, 12000),
        "OTHER": ("Miscellaneous farm expenses", 200, 3000),
    }

    EXPENSES_PER_CYCLE = 4

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT f.farm_id, fi.field_id, pc.cycle_id FROM agripulse.farm AS f INNER JOIN agripulse.field AS fi ON f.farm_id = fi.farm_id INNER JOIN agripulse.planting_cycle AS pc ON fi.field_id = pc.field_id")
            rows = cur.fetchall()
            farm_expenses_to_insert = []
            # generate EXPENSES_PER_CYCLE random expenses for each planting cycle
            for farm_id, field_id, cycle_id in rows:
                for _ in range(EXPENSES_PER_CYCLE):
                    expense_date = date.today() - timedelta(days=random.randint(0, 365))
                    expense_category = random.choice(list(EXPENSES.keys()))
                    description, min_amount, max_amount = EXPENSES[expense_category]
                    amount = round(random.uniform(min_amount, max_amount), 2)
                    farm_expenses_to_insert.append((farm_id, cycle_id, expense_date, expense_category, description, amount))

            cur.executemany(
                """
                INSERT INTO agripulse.farm_expense
                (farm_id, cycle_id, expense_date, expense_category, description, amount)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                farm_expenses_to_insert,
            )
            cur.execute("SELECT COUNT(*) FROM agripulse.farm_expense")
            print(f"Farm expenses added: {cur.fetchone()[0]}")

def generate_customers():
    CUSTOMERS = [
        ("Kalimati Fresh Traders", "WHOLESALER", "Kathmandu"),
        ("Valley Vegetable Suppliers", "WHOLESALER", "Lalitpur"),
        ("Pokhara Agro Distributors", "WHOLESALER", "Kaski"),
        ("Chitwan Produce Hub", "WHOLESALER", "Chitwan"),
        ("Eastern Harvest Traders", "WHOLESALER", "Morang"),
        ("Green Basket Retail", "RETAILER", "Kathmandu"),
        ("Fresh Choice Mart", "RETAILER", "Lalitpur"),
        ("Pokhara Daily Market", "RETAILER", "Kaski"),
        ("Bharatpur Fresh Mart", "RETAILER", "Chitwan"),
        ("Biratnagar Grocery Center", "RETAILER", "Morang"),
        ("Himalayan Kitchen", "RESTAURANT", "Kathmandu"),
        ("Garden Cafe", "RESTAURANT", "Lalitpur"),
        ("Lakeside Food House", "RESTAURANT", "Kaski"),
        ("Chitwan Family Restaurant", "RESTAURANT", "Chitwan"),
        ("Terai Spice Kitchen", "RESTAURANT", "Rupandehi"),
        ("Nepal Food Processing", "PROCESSOR", "Kathmandu"),
        ("Terai Agro Processing", "PROCESSOR", "Chitwan"),
        ("Hillside Pickle Producers", "PROCESSOR", "Kaski"),
        ("Fresh Produce Industries", "PROCESSOR", "Morang"),
        ("Valley Food Products", "PROCESSOR", "Lalitpur"),
        ("Ram Bahadur Household", "DIRECT", "Kathmandu"),
        ("Sita Family Farm Buyer", "DIRECT", "Lalitpur"),
        ("Pokhara Home Buyer", "DIRECT", "Kaski"),
        ("Bharatpur Local Buyer", "DIRECT", "Chitwan"),
        ("Biratnagar Home Buyer", "DIRECT", "Morang"),
        ("Dharan Market Customer", "DIRECT", "Sunsari"),
        ("Butwal Fresh Buyer", "DIRECT", "Rupandehi"),
        ("Janakpur Local Buyer", "DIRECT", "Dhanusha"),
        ("Hetauda Household Buyer", "DIRECT", "Makwanpur"),
        ("Nepalgunj Local Buyer", "DIRECT", "Banke"),
    ]
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            for customer_name, customer_type, district in CUSTOMERS:
                cur.execute(
                    """
                    INSERT INTO agripulse.customer (customer_name, customer_type, district)
                    VALUES (%s, %s, %s)
                    """,
                    (customer_name, customer_type, district),
                )
            cur.execute("SELECT COUNT(*) FROM agripulse.customer")
            print(f"Total customers: {cur.fetchone()[0]}")

def generate_sales():

    BASE_PRICES = {
        "Rice": 80,
        "Maize": 45,
        "Wheat": 55,
        "Apple": 220,
        "Mango": 120,
        "Mustard": 100,
        "Lentil": 160,
        "Potato": 45,
        "Tomato": 70,
        "Cauliflower": 65,
        "Cabbage": 45,
        "Chili": 180,
        "Cucumber": 55,
    }
    
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT h.harvest_id, h.quantity_kg, h.harvest_date, c.crop_name
                        FROM agripulse.harvest h JOIN agripulse.planting_cycle pc
                        ON pc.cycle_id = h.cycle_id 
                        JOIN agripulse.crop c
                        ON c.crop_id = pc.crop_id
                        ORDER BY h.harvest_id""")
            harvests = cur.fetchall()
            cur.execute("""SELECT customer_id FROM agripulse.customer ORDER BY customer_id""")
            customers = cur.fetchall()
            sales_to_insert = []
            for harvest_id, quantity_kg, harvest_date, crop_name in harvests:
                # generate a random number of sales between 1 and 3 for each harvested planting cycle
                num_sales = random.randint(1, 3)
                for _ in range(num_sales):
                    sale_date = harvest_date + timedelta(days=random.randint(0, 7))
                    customer_id = random.choice(customers)[0]
                    #sell between 10% and 30% of the harvested quantity for each sale
                    quantity_kg = round(float(quantity_kg) * random.uniform(0.1, 0.3), 2)
                    price_per_kg = BASE_PRICES.get(crop_name, 75) + round(random.uniform(-5.0, 5.0), 2)
                    sales_to_insert.append((harvest_id, customer_id, sale_date, quantity_kg, price_per_kg))

            cur.executemany(
                """
                INSERT INTO agripulse.sale
                (harvest_id ,customer_id, sale_date, quantity_kg, price_per_kg)
                VALUES (%s, %s, %s, %s, %s)
                """,
                sales_to_insert,
            )
            cur.execute("SELECT COUNT(*) FROM agripulse.sale")
            print(f"Sales records added: {cur.fetchone()[0]}")

def main():
        delete_existing_data()
        generate_farms()
        generate_fields()
        generate_weather_observations()
        generate_crops()
        generate_planting_cycles()
        generate_harvests()
        generate_irrigation_events()
        generate_fertilizer_applications()
        generate_soil_measurements()
        generate_disease_observations()
        generate_market_prices()
        generate_farm_expenses()
        generate_customers()
        generate_sales()

if __name__ == "__main__":
    main()
