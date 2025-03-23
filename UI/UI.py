import tkinter as tk
from tkinter import messagebox

class WatchdogAIUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WatchdogAI")
        self.root.geometry("400x300")

        ##Title Label##
        self.title_label = tk.Label(root, text="Welcome to WatchdogAI", font=("Arial", 16))
        self.title_label.pack(pady=10)

        ## Input Section ##
        self.input_label = tk.Label(root, text="Enter Data:", font=("Arial", 12))
        self.input_label.pack(pady=5)

        self.input_entry = tk.Entry(root, width=30)
        self.input_entry.pack(pady=5)

        self.submit_button = tk.Button(root, text="Submit", command=self.submit_data)
        self.submit_button.pack(pady=10)

        ## Exit Button ##
        self.exit_button = tk.Button(root, text="Exit", command=root.quit)
        self.exit_button.pack(pady=10)

    def submit_data(self):
        user_input = self.input_entry.get()
        if user_input:
            messagebox.showinfo("Submission Successful", f"You entered: {user_input}")
        else:
            messagebox.showwarning("Input Error", "Please enter some data!")

if __name__ == "__main__":
    root = tk.Tk()
    app = WatchdogAIUI(root)
    root.mainloop()