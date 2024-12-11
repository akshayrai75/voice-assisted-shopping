import os
import re
import subprocess
from typing import Annotated

from fastapi import FastAPI, Depends, status, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from google.cloud import speech, texttospeech, dialogflow
from pydantic import BaseModel
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, sessionmaker

import db_models
import google_cloud_service
from db_connect import db_engine, SessionLocal

app = FastAPI()
db_models.Base.metadata.create_all(bind=db_engine)

# Global dictionary to keep track of in-progress carts
in_progress_carts = {}

# Function to get a new DB session
def get_db_session(engine):
    try:
        Session = sessionmaker(bind=engine)
        session = Session()
        return session
    except Exception as ex:
        print("Error getting DB session: ", ex)
        return None

# Database connection dependency
def connect_to_db():
    db_connection = SessionLocal()
    try:
        yield db_connection
    finally:
        db_connection.close()

db_dependency = Annotated[Session, Depends(connect_to_db)]

# Base Models for API
class ItemBaseModel(BaseModel):
    name: str
    company: str
    price: float

class CustomerBaseModel(BaseModel):
    username: str

class OrderBaseModel(BaseModel):
    id: int
    items: str
    total_price: float
    status: str

# CRUD operations for Customer, Order, and Item models
@app.post("/customer/", status_code=status.HTTP_201_CREATED)
async def create_customer(customer: CustomerBaseModel, db: db_dependency):
    new_customer = db_models.Customer(**customer.dict())
    db.add(new_customer)
    db.commit()

@app.post("/order/", status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderBaseModel, db: db_dependency):
    new_order = db_models.Order(**order.dict())
    db.add(new_order)
    db.commit()

@app.get("/order/{id}", status_code=status.HTTP_200_OK)
async def get_order(id: int, db: db_dependency):
    try:
        order = db.query(db_models.Order).filter(db_models.Order.id == id).one()
        return order
    except NoResultFound:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"message": "Order not found"})

@app.post("/item/", status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemBaseModel, db: db_dependency):
    new_item = db_models.Item(**item.dict())
    db.add(new_item)
    db.commit()

# Endpoint for processing chatbot audio
@app.post('/audio-chatbot')
async def process_chatbot_audio(session: str = Form(...), fname: str = Form(...), data: UploadFile = File(...)):
    # Save uploaded audio file
    audio_data = await data.read()
    with open(fname, 'wb') as f:
        f.write(audio_data)

    # Convert audio file to mp3 format
    input_audio = "input.mp3"
    command = f"ffmpeg -i \"{fname}\" -vn -ab 128k -ar 44100 -y \"{input_audio}\""
    subprocess.call(command, shell=True)

    # Setup Google Cloud clients
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '<YOUR GOOGLE CLOUD DIALOGFLOW API KEY>.json'
    s2t_client = speech.SpeechClient()
    df_client = dialogflow.SessionsClient()
    t2s_client = texttospeech.TextToSpeechClient()

    # Perform Speech-to-Text
    query = google_cloud_service.speech_to_text(input_audio=input_audio, client=s2t_client, sample_rate_hertz=44100)

    # Perform Dialogflow query
    language_code = "en-US"
    project_id = "va-shopping-chatbot"
    df_response = google_cloud_service.query_dialogeflow(
        text=query, session_id=session, language_code=language_code, project_id=project_id, client=df_client)

    # Perform Text-to-Speech
    t2s_response = google_cloud_service.text_to_speech(query_reply=df_response, client=t2s_client)

    # Save and return the synthesized speech
    output_audio_file = '../../../practice/chatbot/shopper_chatbot/output.mp3'
    with open(output_audio_file, "wb") as out:
        out.write(t2s_response)

    return FileResponse(output_audio_file, media_type='audio/mpeg')

# Helper functions for handling various intents
def process_intent(intent, response_parameters, session_id: str):
    match intent:
        case 'track.order':
            return track_order(response_parameters)
        case 'add.items':
            return add_order(response_parameters, session_id)
        case 'order.brand':
            return get_available_brands(response_parameters, session_id)
        case 'view.cart':
            return get_session_cart_items(session_id)
        case 'place.the.order':
            return complete_order(session_id)
        case 'remove.from.cart':
            return remove_order(response_parameters, session_id)
        case default:
            return ('I could not understand you. Please say "New Order" for placing a new order or "track order" to '
                    'track an order. Also, only items available to add in your orders are "Milk", "Bread", "Eggs", '
                    '"Sugar", "Salt", "Oil", "Tomato Ketchup", "Water" and "Noodles". For example, you can say "add '
                    'two eggs".')

def track_order(order_parameters: dict):
    print("WORKING INTENT: TRACK ORDER")
    order_id = order_parameters['order_id']
    print(order_id)
    order_status = ""
    try:
        db_session = get_db_session(engine=db_engine)
        order_status = db_session.query(db_models.Order.status).filter(db_models.Order.id == int(order_id)).first()
        db_session.close()
    except NoResultFound:
        print("NO DATA FOUND")

    if order_status:
        response_text = f"The order status for order id {order_id} is {order_status[0]}"
    else:
        response_text = f"No Order found with id {int(order_id)}"

    return response_text

def add_order(order_parameters: dict, session_id: str):
    print("WORKING INTENT: ADD ORDER")
    print("Session for ADD: " + session_id)
    grocery_items = order_parameters['grocery-item']
    grocery_quantity = order_parameters['number']

    if len(grocery_items) != len(grocery_quantity):
        response_text = "Sorry, I did not get that. Please specify grocery items and their quantities clearly."
    else:
        new_cart_item = {item: {'quantity': int(qty)} for item, qty in zip(grocery_items, grocery_quantity)}
        if session_id in in_progress_carts:
            current_grocery_cart = in_progress_carts[session_id]
            current_grocery_cart.update(new_cart_item)
            in_progress_carts[session_id] = current_grocery_cart
        else:
            in_progress_carts[session_id] = new_cart_item

        print(in_progress_carts[session_id])
        list_of_items = list(in_progress_carts[session_id].keys())
        list_of_items_without_brand = [item for item in list_of_items if "brand" not in in_progress_carts[session_id][item].keys()]

        response_text = get_item_choices(list_of_items_without_brand)

    return response_text

def get_session_cart_items(session_id):
    print("VIEW CART")
    cart_item_info_str = convert_cart_items_to_str(in_progress_carts[session_id])
    return (f"In your cart, you have {cart_item_info_str}. And your total to pay is {get_total_cart_value(session_id)}."
            f" Do you need anything else?")

def remove_order(order_parameters: dict, session_id: str):
    print("WORKING INTENT: REMOVE ORDER for: " + session_id)
    print("IN PROGRESS CARTS: ", in_progress_carts[session_id])

    if session_id not in in_progress_carts:
        return "Sorry, Couldn't find your order. Please place a new order by saying \"NEW ORDER\"."

    grocery_items = order_parameters['grocery-item']
    present_cart = in_progress_carts[session_id]

    removed_grocery_items = []
    unknown_grocery_items = []

    for grocery_item in grocery_items:
        if grocery_item not in present_cart:
            unknown_grocery_items.append(grocery_item)
        else:
            removed_grocery_items.append(grocery_item)
            del present_cart[grocery_item]

    response_text = ""
    if removed_grocery_items:
        response_text = f'Items {", ".join(removed_grocery_items)} are now removed from your cart.'
    if unknown_grocery_items:
        response_text += f' You don\'t have the following items in your cart: {", ".join(unknown_grocery_items)}'
    if not present_cart:
        response_text += " Your cart is empty."
    else:
        response_text += f" You have the following items in your cart: {convert_cart_items_to_str(present_cart)}"

    return response_text

def complete_order(session_id: str):
    print("WORKING INTENT: COMPLETE ORDER for: " + session_id)

    if session_id not in in_progress_carts:
        return "Sorry, Couldn't find your order. Please place a new order by saying \"NEW ORDER\"."
    else:
        order_id, total_price = save_order(cart=in_progress_carts[session_id], session_id=session_id)
        if order_id == -1:
            return "Sorry, I was not able to place order at the moment. Please place a new one after some time."
        else:
            response_text = (f"Your order for ${total_price} is placed successfully and your new order id is {order_id}"
                             f". Please use your order id to track your delivery. Thank you.")
        del in_progress_carts[session_id]

    return response_text

def save_order(cart: dict, session_id: str):
    order_id = -1
    total_price = get_total_cart_value(session_id)
    current_cart = in_progress_carts[session_id]

    items = []

    for item, details in current_cart.items():
        item_details = f"{item}|{details['brand']}|{details['price']}|{details['quantity']}"
        items.append(item_details)

    result = ", ".join(items)
    print(result)

    new_order = db_models.Order(items=items, total_price=total_price)
    db_session = get_db_session(engine=db_engine)

    db_session.add(new_order)
    db_session.commit()

    print("ORDER ID")
    print(new_order.id)
    return new_order.id, total_price

def get_available_brands(order_parameters: dict, session_id: str):
    print("WORKING INTENT: CHOOSE BRANDS IN ORDER")
    grocery_items = order_parameters['grocery-item']
    grocery_brands = order_parameters['brand']
    existing_items = in_progress_carts[session_id].keys()
    print("GROCERY ITEMS")
    print(grocery_items)
    print("GROCERY BRANDS")
    print(grocery_brands)
    print("EXISTING ITEMS")
    print(existing_items)

    for item in grocery_items:
        cart_item = in_progress_carts[session_id]
        if item in cart_item:
            index = grocery_items.index(item)
            cart_item[item]['brand'] = grocery_brands[index]
            brand_name = cart_item[item]['brand'] if cart_item[item]['brand'] != "great\xa0value" else "great value"
            cart_item[item]['price'] = round(get_item_prices(item_name=item, item_brand=brand_name)[0], 2)
            in_progress_carts[session_id] = cart_item

    print("EXISTING")
    print(in_progress_carts[session_id])
    cart_item_info_str = convert_cart_items_to_str(in_progress_carts[session_id])
    response_text = f"In your cart, you have {cart_item_info_str}. "

    unbranded_items = [key for key in in_progress_carts[session_id] if "brand" not in in_progress_carts[session_id][key]]
    if unbranded_items:
        response_text += f"You need to specify brands for {unbranded_items}"
    else:
        response_text += "Do you need anything else?"

    return response_text

def get_session_id_from_context(context: str):
    extracted_session_id = re.search(r"/sessions/(.*?)/contexts/", context)
    if extracted_session_id:
        return extracted_session_id.group(1)
    return ""

def convert_cart_items_to_str(grocery_cart: dict):
    cart_items_str = ", ".join([f"{int(value['quantity'])} {value['brand']} {key} " +
                                str('for $' + str(value['price'] * int(value['quantity'])) if value['price'] else '') +
                                f"" for key, value in grocery_cart.items()])
    return cart_items_str

def get_item_choices(items):
    db_session = get_db_session(engine=db_engine)
    available_items = db_session.query(db_models.Item.name, db_models.Item.company, db_models.Item.price).filter(
        db_models.Item.name.in_(items)).all()
    db_session.close()

    available_items_dict = {}
    for item, brand, price in available_items:
        available_items_dict.setdefault(item, set()).add((brand, price))

    available_items_str = ""
    for item, options in available_items_dict.items():
        available_items_str += f"For {item} we have options from: "
        options_list = [f"{brand} for {price}" for brand, price in options]
        available_items_str += ', '.join(options_list)
        available_items_str += ". "

    return available_items_str

def get_item_prices(item_name: str, item_brand: str):
    db_session = get_db_session(engine=db_engine)
    item_price = db_session.query(db_models.Item.price).filter(
        db_models.Item.name == item_name, db_models.Item.company == item_brand).first()
    db_session.close()

    return item_price[0] if item_price else -1

def get_total_cart_value(session_id: str):
    total_price = 0
    current_cart = in_progress_carts[session_id]
    for item in current_cart:
        total_price += (current_cart[item]['price'] if current_cart[item]['price'] else 0) * current_cart[item]['quantity']

    return round(total_price, 2)
