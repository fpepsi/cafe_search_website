from flask import Flask, render_template, redirect, request, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime as dt
import math
import re

app = Flask(__name__)

app.secret_key = "your-secret-key"


# CREATE DB
class Base(DeclarativeBase):
    pass
# Connect to Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafes.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# Cafe TABLE Configuration
class Cafe(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    map_url: Mapped[str] = mapped_column(String(500), nullable=False)
    img_url: Mapped[str] = mapped_column(String(500), nullable=False)
    location: Mapped[str] = mapped_column(String(250), nullable=False)
    seats: Mapped[str] = mapped_column(String(250), nullable=False)
    has_toilet: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_wifi: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_sockets: Mapped[bool] = mapped_column(Boolean, nullable=False)
    can_take_calls: Mapped[bool] = mapped_column(Boolean, nullable=False)
    coffee_price: Mapped[str] = mapped_column(String(250), nullable=True)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


with app.app_context():
    db.create_all()


def extract_coordinates(map_url):
    # Regular expression to match latitude and longitude
    pattern = r"@(-?\d+\.\d+),(-?\d+\.\d+)"
    match = re.search(pattern, map_url)
    if match:
        latitude = float(match.group(1))
        longitude = float(match.group(2))
        return latitude, longitude
    return None, None


def filter_cafes(cafes_database, filter):
    '''Filter the Cafe optins based on user selections'''
    # Create a list of lambda functions containing only active filters
    filters = []
    filters.append(lambda item: float(item['coffee_price'][1:]) <= filter["coffee_price"])
    if filter["location"] and filter["location"] != 'All locations...':
        filters.append(lambda item: item["location"] == filter["location"])
    if filter["has_sockets"]:
        filters.append(lambda item: item["has_sockets"] == 1)
    if filter["has_toilet"]:
        filters.append(lambda item: item["has_toilet"] == 1)
    if filter["has_wifi"]:
        filters.append(lambda item: item["has_wifi"] == 1)
    if filter["seats"] != 'any':
        filters.append(lambda item: item["seats"] == filter["seats"])
    
    print(filter)
    print(filters)
    filtered_cafes = [
        cafe for cafe in cafes_database
        if all(filter_test(cafe) for filter_test in filters)
        ]   
    return filtered_cafes


def get_cafe_range(cafes):
    prices = [float(cafe['coffee_price'][1:]) for cafe in cafes if cafe['coffee_price'][1:]]
    min_price = math.floor(min(prices))
    max_price = math.ceil(max(prices))
    range(min_price, max_price + 1)
    price_range = [float(number) for number in range(min_price, max_price + 1)]
    return price_range


@app.route("/", methods=["GET", "POST"])
def home():
    # database variables used to populate website
    cafes_database = [] # list of dictionaries containing each cafe's attributes, excluding their states
    cafe_price_range = [] # used to populate the price filter slider
    location_list = []  # used to populate the location filter dropdown
    current_year = dt.now().year  # updates website copyright date
    result = db.session.execute(db.select(Cafe).order_by('location'))
    # cleans database query from state variable
    all_cafe_locations = result.scalars().all()
    for cafe in all_cafe_locations:
        cafes_database.append({key: value for key, value in cafe.__dict__.items() if not key.startswith("_")}) 
    # extract coordinates for google maps and add to cafe database
    for cafe in cafes_database:
        map_url = cafe['map_url']
        lat, long = extract_coordinates(map_url)
        cafe['lat'] = lat
        cafe['long'] = long
    # create a location list to parse data on the back end
    location_list = [cafe['location'] for cafe in cafes_database]
    location_list = list(set(location_list))
    location_list.sort()
    cafe_price_range = get_cafe_range(cafes_database)
    selected_cafe_list = cafes_database    

    # Grab user selections
    filter_selection = {
    "location": request.form.get("location", None),
    "has_sockets": request.form.get("sockets", None),
    "has_toilet": request.form.get("toilet", None),
    "has_wifi": request.form.get("wifi", None),
    "seats": request.form.get("seats", "any"),
    "coffee_price": float(request.form.get("coffee_price", cafe_price_range[-1])),
    }  

    if request.method == "POST":
        # Update filter_selection with actual form inputs
        filter_selection = {
            "location": request.form.get("location", None),
            "has_sockets": request.form.get("sockets", None),
            "has_toilet": request.form.get("toilet", None),
            "has_wifi": request.form.get("wifi", None),
            "seats": request.form.get("seats", "any"),
            "coffee_price": float(request.form.get("coffee_price", cafe_price_range[-1])),
        }

        # Process filter options and refresh list of applicable cafes
        if "cafe_selection" not in request.form:
            selected_cafe_list = filter_cafes(cafes_database, filter_selection)

    selected_cafe_id = int(request.form.get("cafe_selection", selected_cafe_list[0]['id']))
    nbr_options = len(selected_cafe_list)
    currency = selected_cafe_list[0]['coffee_price'][0]

    return render_template(
        "index.html",
        title="Cafe Search",
        year=current_year,
        selected_cafe_list=selected_cafe_list,
        location_list=location_list,
        nbr_options=nbr_options,
        cafe_price_range=cafe_price_range,
        filter=filter_selection,
        currency=currency,
        selected_cafe_id=selected_cafe_id,
    )


# HTTP POST - Create Record
@app.route("/add", methods=["GET", "POST"])
def add_cafe():
    if request.method == "POST":
        new_cafe = Cafe(
        name=request.form.get('name'),
        map_url=request.form.get('map_url'),
        img_url=request.form.get('img_url'),
        location=request.form.get('location'),
        seats=request.form.get('seats'),
        has_toilet=bool(request.form.get('has_toilet')),
        has_wifi=bool(request.form.get('has_wifi')),
        has_sockets=bool(request.form.get('has_sockets')),
        can_take_calls=bool(request.form.get('can_take_calls')),
        coffee_price=request.form.get('coffee_price')
        )

        # Input Validation
        errors = []
        print(new_cafe.map_url)

        # Validate name (must be a non-empty string)
        if not isinstance(new_cafe.name, str) or not new_cafe.name.strip():
            errors.append("Cafe name must be a valid non-empty string.")

        # Validate location (optional, but must be a string if provided)
        if not isinstance(new_cafe.location, str) or not new_cafe.location.strip():
            errors.append("Location must be a valid non-empty string.")

        # Validate URL using regex
        url_pattern = re.compile(
            r'^(https?://)?(www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/[^\s]*)?$')
        
        if new_cafe.map_url and not re.match(url_pattern, new_cafe.map_url):
            errors.append("Please provide a valid URL for the Map.")

        if new_cafe.img_url and not re.match(url_pattern, new_cafe.img_url):
            errors.append("Please provide a valid URL for the image.")

        # Validate price (must be a positive number)
        try:
            new_cafe.coffee_price = float(new_cafe.coffee_price)
            if new_cafe.coffee_price <= 0:
                errors.append("Price must be a positive number.")
        except (ValueError, TypeError):
            errors.append("Price must be a valid number in the format #.##.")

        # If there are errors, show them to the user
        if errors:
            for error in errors:
                flash(error, "Error on inputs")
            return render_template("suggest.html")  # Return the form with errors

        # Process and save the cafe (if no validation errors)
        db.session.add(new_cafe)
        db.session.commit()
        flash("Cafe successfully added!", "success")
        return redirect(url_for("add_cafe"))
    
    return render_template("suggest.html", title="Suggest Cafe")


if __name__ == '__main__':
    app.run(debug=True)
