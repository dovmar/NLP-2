from flask import Flask
from flask_assistant import Assistant, ask, tell, context_manager, event
import pandas as pd
import numpy as np
import os

app = Flask(__name__)
assist = Assistant(app, route='/',project_id="paskaita-vdul")

df = pd.read_pickle("df.pkl")

x = df[~df["subtype"].duplicated()].copy()
x["url"] = x["url"].str.extract("(.+/)")
x = x[["url","subtype"]]
dictionary_of_urls = {}
for i in range(len(x)):
    dictionary_of_urls[x.iloc[i,1]] = x.iloc[i,0]
    
items_indices = None
df_items = None  

@assist.action('available_items')
def available_items_action():
    df2 = df[~df["description"].duplicated()]
    length = len(df2)
    min = df.iloc[:,12].min()
    max = df.iloc[:,12].max()
    speech = f"There are {length} unique items in the store ranging from {min} to {max} euros"
    return tell(speech)


@assist.action('find_category')
def find_category_action(category):
    return tell("You can find " + category + " in " + dictionary_of_urls[category])


@assist.action('find_items',mapping={'price': 'sys.unit-currency'},default={"price_status":"cheap"})
def find_items_action(category,price_status,price,size):
    
    global df_items
    df_items = df[df["subtype"]==category]
    if size is not None:
        size_series = df_items.iloc[:,8] * df_items.iloc[:,9] * df_items.iloc[:,10]
        size_max = size_series.max()
        if size == "small":
            df_items = df_items[size_series < size_max * 0.25]
        elif size == "small":
            df_items = df_items[(size_series > size_max * 0.25) & (size_series < size_max * 0.75)]
        else:
            df_items = df_items[size_series > size_max * 0.75]
            
    if price_status is not None:
        price_max = df_items["price"].max()
        if price_status == "cheap":
            df_items = df_items[df_items["price"] < price_max * 0.25]
        elif price_status == "expensive":
            df_items = df_items[df_items["price"] > price_max * 0.75]
        elif price_status in ["under","over"] and price is not None:
            if price_status == "under":
                df_items = df_items[df_items["price"] < price["amount"]]
            else:
                df_items = df_items[df_items["price"] > price["amount"]]
    
    if len(df_items) > 0:
        global items_indices
        items_indices = list(df_items.index)
        context_manager.add("items_found",lifespan=1)
        answer = tell("I have found " + str(len(df_items)) + " matching that description").\
        add_msg("Would you like to take a look at a few of them?")     
    else:
        answer = tell("There seems to be no matches for what you have described")   
            
    return answer



def smart_truncate(content, length=55, suffix='...'):
    if len(content) <= length:
        return content
    else:
        return ' '.join(content[:length+1].split(' ')[0:-1]) + suffix
    

@assist.context('item_found')
@assist.action("find_items - yes")
def find_items_yes_action():
    answer = tell("Some of the items that match that description:")
    length = len(items_indices)
    print(items_indices)
    for i in range(0,min(length,3)):
        j = items_indices.pop()
        answer.add_msg(df_items.loc[j,"title"] + "\n\n" + smart_truncate(df_items.loc[j,"description"]) + "\n\n" + df_items.loc[j,"url"])
    if len(items_indices) > 0:
        context_manager.add("find_items-followup",lifespan=1)
        context_manager.add("items_found",lifespan=1)
        answer.add_msg("Would you like to see the rest of the items?")
    return answer
    

@assist.context('item_found')
@assist.action("find_items - extremes")
def find_items_extremes_action(price_status,size):
    
    answer = tell("I can't find that item")
    if price_status is not None:
        if price_status == "cheap":
            j = df_items.iloc[:,12].idxmin() 
            answer = tell(df_items.loc[j,"title"] + "\n\n" + smart_truncate(df_items.loc[j,"description"]) + "\n\n" + df_items.loc[j,"url"])
        if price_status == "expensive":
            j = df_items.iloc[:,12].idxmax() 
            answer = tell(df_items.loc[j,"title"] + "\n\n" + smart_truncate(df_items.loc[j,"description"]) + "\n\n" + df_items.loc[j,"url"])
    elif price_status is None and size is not None:
        size_series = df_items.iloc[:,8] * df_items.iloc[:,9] * df_items.iloc[:,10]
        if size == "small":
            j = size_series.idxmin() 
            answer = tell(df_items.loc[j,"title"] + "\n\n" + smart_truncate(df_items.loc[j,"description"]) + "\n\n" + df_items.loc[j,"url"])
        if size == "big":
            j = size_series.idxmax() 
            answer = tell(df_items.loc[j,"title"] + "\n\n" + smart_truncate(df_items.loc[j,"description"]) + "\n\n" + df_items.loc[j,"url"])
    context_manager.add("find_items-followup",lifespan=1)
    context_manager.add("items_found",lifespan=1)
    return answer



if __name__ == '__main__':
    app.run(debug=True)
    

