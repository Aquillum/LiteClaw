from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import subprocess
import os
from .config import settings

class WhatsAppDriver:
    def __init__(self):
        self.driver = None
        self.is_connected = False
        self.official_number = None

    def launch_and_attach(self):
        """
        Launches Chrome in debug mode if not running, then attaches.
        """
        if self._try_attach():
            print("[WhatsApp] Attached to Existing Chrome.")
            return

        print("[WhatsApp] Chrome not found. Launching new instance...")
        try:
            cmd = [
                settings.CHROME_PATH,
                f"--remote-debugging-port={settings.CHROME_DEBUG_PORT}",
                f"--user-data-dir={settings.CHROME_USER_DATA_DIR}",
                "https://web.whatsapp.com"
            ]
            # Use Popen to launch independent process
            subprocess.Popen(cmd)
            time.sleep(5) # Wait for launch
            
            if self._try_attach():
                print("[WhatsApp] Launched and Attached.")
            else:
                print("[WhatsApp] Failed to attach after launch.")
                
        except Exception as e:
            print(f"[WhatsApp] Error launching Chrome: {e}")

    def _try_attach(self):
        try:
            options = Options()
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{settings.CHROME_DEBUG_PORT}")
            self.driver = webdriver.Chrome(options=options)
            # Verify we are on whatsapp
            if "whatsapp" not in self.driver.current_url:
                self.driver.get("https://web.whatsapp.com")
            self.is_connected = True
            return True
        except Exception:
            self.is_connected = False
            return False
            
    def attach(self):
        self.launch_and_attach()

    def send_message(self, phone_number: str, message: str):
        if not self.driver or not self.is_connected:
            self.launch_and_attach()
            if not self.is_connected:
                return False
        
        try:
            phone = phone_number.replace("+", "").replace(" ", "")
            url = f"https://web.whatsapp.com/send?phone={phone}"
            self.driver.get(url)
            
            wait = WebDriverWait(self.driver, 20)
            inp_xpath = '//div[@contenteditable="true"][@data-tab="10"]'
            
            try:
                # Wait for input box
                input_box = wait.until(EC.presence_of_element_located((By.XPATH, inp_xpath)))
                
                for line in message.split('\n'):
                     input_box.send_keys(line)
                     input_box.send_keys(Keys.SHIFT + Keys.ENTER)
                
                input_box.send_keys(Keys.ENTER)
                time.sleep(1) 
                return True
            except Exception as e:
                print(f"[WhatsApp] Error finding input box: {e}")
                return False

        except Exception as e:
            print(f"[WhatsApp] Error sending message: {e}")
            return False

    def check_for_unread_messages(self):
        """
        Polls for unread messages.
        Note: This is a robust-but-fragile implementation dependent on WhatsApp Web classes.
        """
        if not self.driver or not self.is_connected:
            return []
            
        results = []
        try:
            # Look for elements with 'aria-label' containing "unread message"
            # This is a generic semantic selector that is more robust than class obfuscation
            unread_chats = self.driver.find_elements(By.XPATH, '//span[contains(@aria-label, "unread message")]/ancestor::div[@role="row"]')
            
            for chat_row in unread_chats:
                try:
                    # Click the chat to open it (marks as read implicitly)
                    chat_row.click()
                    time.sleep(1)
                    
                    # Get the sender name/number (from header)
                    header_title = self.driver.find_element(By.XPATH, '//header//div[@role="button"]//span[@title]')
                    sender = header_title.text
                    
                    # Get the last message
                    # Find all message containers
                    msgs = self.driver.find_elements(By.XPATH, '//div[@role="row"]//div[contains(@class, "message-in")]//span[@class="_11JPr selectable-text copyable-text"]')
                    if msgs:
                        last_msg = msgs[-1].text
                        if last_msg:
                           results.append((sender, last_msg))
                           
                except Exception as e:
                    print(f"Error processing chat row: {e}")
                    continue
                    
        except Exception as e:
            # print(f"[WhatsApp] Polling error: {e}") 
            pass
        
        return results

# Singleton instance
wa_driver = WhatsAppDriver()
