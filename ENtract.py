import re
import time
import csv
import tkinter as tk
from tkinter import messagebox, filedialog
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from threading import Thread

def login(driver, email, password):
    driver.get("https://www.linkedin.com/login")
    time.sleep(2)
    driver.find_element(By.ID, "username").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password + Keys.RETURN)
    time.sleep(5)

def load_post(driver, post_url):
    driver.get(post_url)
    time.sleep(5)

    try:
        filter_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Most relevant')]"))
        )
        filter_button.click()
        time.sleep(1)

        most_recent = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Most recent']/ancestor::div[@role='button']"))
        )
        driver.execute_script("arguments[0].click();", most_recent)
        time.sleep(3)
    except Exception as e:
        print("Could not switch to 'Most recent':", e)

    last_click_time = time.time()

    while True:
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(1)

        try:
            more_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'more comments')]")
            clicked = False
            for btn in more_buttons:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    print("Clicked 'Load more comments'")
                    clicked = True
                    last_click_time = time.time()
                    time.sleep(2)
            if not clicked:
                print("No visible 'Load more comments' buttons right now.")
        except Exception as e:
            print("Error while trying to click 'Load more comments':", e)

        if time.time() - last_click_time > 90:
            print("No new comments loaded in 90 seconds. Exiting loop.")
            break

def extract_emails_and_names(driver, temp_path="temp_scraped_data.csv"):
    comments = driver.find_elements(By.XPATH, "//div[contains(@class, 'comments-comment-item')]")
    data = set()

    with open(temp_path, "w", newline='', encoding="utf-8") as temp_file:
        writer = csv.writer(temp_file)
        writer.writerow(["Name", "Email"])

        for comment in comments:
            try:
                content_elem = comment.find_element(By.XPATH, ".//div[contains(@class, 'comments-comment-item__main-content')]")
                comment_text = content_elem.text

                try:
                    name_elem = comment.find_element(By.XPATH, ".//span[contains(@class, 'comments-post-meta__name-text')]")
                    name = name_elem.text.split()[0]
                except Exception:
                    name = "Unknown"

                emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', comment_text)
                for email in emails:
                    key = (name, email.lower())
                    if key not in data:
                        data.add(key)
                        writer.writerow([name, email.lower()])
                        print(f"Extracted: {name} - {email.lower()}")

            except Exception as e:
                print("Error extracting comment:", e)
                continue

    return data

def start_extraction(email, password, post_url):
    driver = None
    temp_file = "temp_scraped_data.csv"
    data = set()

    try:
        service = Service('./chromedriver.exe')
        driver = webdriver.Chrome(service=service)

        login(driver, email, password)
        load_post(driver, post_url)
        data = extract_emails_and_names(driver, temp_path=temp_file)

    except Exception as e:
        messagebox.showerror("Error", f"Error occurred: {str(e)}\nProgress saved to {temp_file}")
    finally:
        if driver:
            driver.quit()

        if data:
            filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
            if filepath:
                with open(filepath, "w", newline='', encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Name", "Email"])
                    for name, email in sorted(data):
                        writer.writerow([name, email])
                messagebox.showinfo("Done", f"{len(data)} entries saved to {filepath}")
        else:
            messagebox.showinfo("No Data", f"No emails were successfully extracted.\nPartial data may be in {temp_file}")

def run_gui():
    def on_submit():
        email = email_entry.get()
        password = password_entry.get()
        url = url_entry.get()
        if not (email and password and url):
            messagebox.showwarning("Missing Info", "Please fill in all fields.")
            return
        Thread(target=start_extraction, args=(email, password, url)).start()

    app = tk.Tk()
    app.title("LinkedIn Email Extractor with Names")
    app.geometry("400x250")

    tk.Label(app, text="LinkedIn Email").pack(pady=5)
    email_entry = tk.Entry(app, width=40)
    email_entry.pack()

    tk.Label(app, text="Password").pack(pady=5)
    password_entry = tk.Entry(app, show="*", width=40)
    password_entry.pack()

    tk.Label(app, text="LinkedIn Post URL").pack(pady=5)
    url_entry = tk.Entry(app, width=40)
    url_entry.pack()

    tk.Button(app, text="Extract Emails & Names", command=on_submit, bg="#4CAF50", fg="white").pack(pady=20)

    app.mainloop()

if __name__ == "__main__":
    run_gui()
