import base64
import requests
import sqlite3
from tkinter import Tk, filedialog, messagebox, Toplevel, Label, simpledialog

# OpenAI API Key
api_key = "env.api_key_here"

# Database setup
def setup_database():
    conn = sqlite3.connect('id_data.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS id_data (
        id INTEGER PRIMARY KEY
    )''')
    conn.commit()
    return conn, cursor

def add_column_if_not_exists(cursor, column_name):
    cursor.execute(f"PRAGMA table_info(id_data)")
    columns = [info[1] for info in cursor.fetchall()]
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE id_data ADD COLUMN {column_name} TEXT")

def insert_or_update_data(cursor, field_name, field_value):
    add_column_if_not_exists(cursor, field_name)
    cursor.execute(f"INSERT INTO id_data ({field_name}) VALUES (?)", (field_value,))
    cursor.connection.commit()

def fetch_all_data(cursor):
    cursor.execute("SELECT * FROM id_data")
    rows = cursor.fetchall()
    return rows

# Image processing and OpenAI API interaction
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def select_image():
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select an Image",
        filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
    )
    return file_path

def show_response(response_text):
    root = Tk()
    root.withdraw()
    messagebox.showinfo("API Response", response_text)

def show_loading():
    root = Tk()
    root.withdraw()
    loading_dialog = Toplevel(root)
    loading_dialog.title("Loading")
    
    loading_dialog.geometry("300x150")
    
    Label(loading_dialog, text="Processing image, please wait...", font=("Arial", 12)).pack(padx=20, pady=20)
    
    root.update_idletasks()
    return loading_dialog

def close_loading(loading_dialog):
    loading_dialog.destroy()

def read_from_database():
    conn, cursor = setup_database()
    all_data = fetch_all_data(cursor)
    conn.close()
    
    # Display the fetched data
    data_string = "\n".join(str(row) for row in all_data)
    root = Tk()
    root.withdraw()
    messagebox.showinfo("Database Data", data_string)

# Main logic
def main():
    conn, cursor = setup_database()

    root = Tk()
    root.withdraw()
    action = simpledialog.askstring("Action", "Enter 'read' to read from database or 'process' to process a new image:")

    if action == 'read':
        read_from_database()
    elif action == 'process':
        image_path = select_image()
        if not image_path:
            print("No image selected.")
            return

        base64_image = encode_image(image_path)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What’s in this image?"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }

        try:
            loading_dialog = show_loading()

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
            close_loading(loading_dialog)

            response_data = response.json()
            response_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "No response content")

            show_response(response_text)

            # Process and insert data into the database
            fields = response_text.split("\n")  # Adjust this according to the actual response format
            for field in fields:
                if field.strip():
                    field_name, field_value = field.split(":")  # Assuming 'field_name: field_value' format
                    insert_or_update_data(cursor, field_name.strip(), field_value.strip())

            # Fetch and display all data
            all_data = fetch_all_data(cursor)
            print("Data in the database:")
            for row in all_data:
                print(row)

        except requests.Timeout:
            close_loading(loading_dialog)
            show_response("The request timed out. Please try again with a smaller image or check your network connection.")
        except Exception as e:
            close_loading(loading_dialog)
            show_response(f"An error occurred: {str(e)}")
    else:
        print("Invalid action.")

if __name__ == "__main__":
    main()
