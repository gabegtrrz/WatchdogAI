import tkinter as tk
from tkinter import messagebox, ttk, filedialog

class WatchdogAIUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WatchdogAI - Procurement Officer Dashboard")
        self.root.geometry("800x600")

        # Main Frame
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Title Label
        self.title_label = tk.Label(self.main_frame, text="WatchdogAI", font=("Arial", 16, "bold"))
        self.title_label.pack(pady=10)

        # Tabbed Interface
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill="both", expand=True)

        # Upload Tab
        self.upload_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.upload_tab, text="Upload Procurement Data")
        self.setup_upload_tab()

        # Transaction View Tab
        self.transaction_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.transaction_tab, text="Transaction View")
        self.setup_transaction_tab()

        # Reports Tab (Placeholder)
        self.reports_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.reports_tab, text="Reports")
        self.setup_reports_tab()

        # Exit Button
        self.exit_button = tk.Button(self.main_frame, text="Exit", command=root.quit)
        self.exit_button.pack(pady=10)

    def setup_upload_tab(self):
        """Set up the Upload Procurement Data tab."""
        # Upload Section
        self.upload_frame = tk.LabelFrame(self.upload_tab, text="Upload Transaction CSV File", font=("Arial", 12))
        self.upload_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.upload_label = tk.Label(self.upload_frame, text="Choose a CSV file:", font=("Arial", 10))
        self.upload_label.pack(pady=5)

        self.upload_button = tk.Button(self.upload_frame, text="Upload File", command=self.upload_file)
        self.upload_button.pack(pady=5)

        self.upload_info = tk.Label(self.upload_frame, text="File must contain: item_id, quantity, unit_price, procurement_method_name, supplier, transaction_date", font=("Arial", 10))
        self.upload_info.pack(pady=5)

        # Upload Status
        self.status_frame = tk.LabelFrame(self.upload_tab, text="Upload Status", font=("Arial", 12))
        self.status_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.upload_status = tk.Label(self.status_frame, text="", font=("Arial", 10))
        self.upload_status.pack(pady=5)

    def setup_transaction_tab(self):
        """Set up the Transaction View tab."""
        # Transaction View Section
        self.transaction_frame = tk.LabelFrame(self.transaction_tab, text="Transaction View", font=("Arial", 12))
        self.transaction_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Filters
        self.filters_frame = tk.Frame(self.transaction_frame)
        self.filters_frame.pack(fill="x", pady=5)

        self.start_date_label = tk.Label(self.filters_frame, text="Start Date:")
        self.start_date_label.pack(side="left", padx=5)
        self.start_date_entry = tk.Entry(self.filters_frame, width=12)
        self.start_date_entry.insert(0, "2025-03-01")
        self.start_date_entry.pack(side="left")

        self.end_date_label = tk.Label(self.filters_frame, text="End Date:")
        self.end_date_label.pack(side="left", padx=5)
        self.end_date_entry = tk.Entry(self.filters_frame, width=12)
        self.end_date_entry.insert(0, "2025-04-04")
        self.end_date_entry.pack(side="left")

        self.supplier_label = tk.Label(self.filters_frame, text="Supplier:")
        self.supplier_label.pack(side="left", padx=5)
        self.supplier_var = tk.StringVar()
        self.supplier_dropdown = ttk.Combobox(self.filters_frame, textvariable=self.supplier_var, state="readonly")
        self.supplier_dropdown.pack(side="left", padx=5)

        self.method_label = tk.Label(self.filters_frame, text="Procurement Method:")
        self.method_label.pack(side="left", padx=5)
        self.method_var = tk.StringVar()
        self.method_dropdown = ttk.Combobox(self.filters_frame, textvariable=self.method_var, state="readonly")
        self.method_dropdown.pack(side="left", padx=5)

        self.filter_button = tk.Button(self.filters_frame, text="Filter", command=self.filter_transactions)
        self.filter_button.pack(side="left", padx=5)

        # Transaction Table
        self.transaction_tree = ttk.Treeview(self.transaction_frame, columns=("ID", "Item", "Qty", "Unit Price", "Method", "Supplier"), show="headings")
        self.transaction_tree.heading("ID", text="Transaction ID")
        self.transaction_tree.heading("Item", text="Item Name")
        self.transaction_tree.heading("Qty", text="Qty")
        self.transaction_tree.heading("Unit Price", text="Unit Price")
        self.transaction_tree.heading("Method", text="Procurement Method")
        self.transaction_tree.heading("Supplier", text="Supplier")
        self.transaction_tree.pack(fill="both", expand=True, pady=5)

        # Pagination
        self.pagination_frame = tk.Frame(self.transaction_frame)
        self.pagination_frame.pack(fill="x", pady=5)

        self.prev_button = tk.Button(self.pagination_frame, text="Previous", command=self.prev_page)
        self.prev_button.pack(side="left", padx=5)

        self.page_label = tk.Label(self.pagination_frame, text="Page 1 of 5")
        self.page_label.pack(side="left", padx=5)

        self.next_button = tk.Button(self.pagination_frame, text="Next", command=self.next_page)
        self.next_button.pack(side="left", padx=5)

        # Anomaly Detection Section
        self.anomaly_frame = tk.LabelFrame(self.transaction_tab, text="Anomaly Detection", font=("Arial", 12))
        self.anomaly_frame.pack(fill="x", padx=5, pady=5)

        self.contamination_label = tk.Label(self.anomaly_frame, text="Contamination (0.0-0.5):")
        self.contamination_label.pack(side="left", padx=5)
        self.contamination_entry = tk.Entry(self.anomaly_frame, width=10)
        self.contamination_entry.insert(0, "0.1")
        self.contamination_entry.pack(side="left", padx=5)

        self.run_anomaly_button = tk.Button(self.anomaly_frame, text="Run Anomaly Detection", command=self.run_anomaly_detection)
        self.run_anomaly_button.pack(side="left", padx=5)

        # Anomaly Results Section
        self.anomaly_results_frame = tk.LabelFrame(self.transaction_tab, text="Anomaly Results", font=("Arial", 12))
        self.anomaly_results_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.anomaly_tree = ttk.Treeview(self.anomaly_results_frame, columns=("ID", "Item", "Unit Price", "Method", "Score"), show="headings")
        self.anomaly_tree.heading("ID", text="Transaction ID")
        self.anomaly_tree.heading("Item", text="Item Name")
        self.anomaly_tree.heading("Unit Price", text="Unit Price")
        self.anomaly_tree.heading("Method", text="Procurement Method")
        self.anomaly_tree.heading("Score", text="Anomaly Score")
        self.anomaly_tree.pack(fill="both", expand=True, pady=5)

        self.export_button = tk.Button(self.anomaly_results_frame, text="Export Anomalies to CSV", command=self.export_anomalies)
        self.export_button.pack(pady=5)

        # Blockchain Integrity Section
        self.blockchain_frame = tk.LabelFrame(self.transaction_tab, text="Blockchain Integrity Status", font=("Arial", 12))
        self.blockchain_frame.pack(fill="x", padx=5, pady=5)

        self.check_date_label = tk.Label(self.blockchain_frame, text="Check Date: 2023-04-04")
        self.check_date_label.pack(side="left", padx=5)
        self.status_label = tk.Label(self.blockchain_frame, text="Status: Valid")
        self.status_label.pack(side="left", padx=5)

    def setup_reports_tab(self):
        """Set up the Reports tab (placeholder)."""
        self.reports_label = tk.Label(self.reports_tab, text="Reports Section (Coming Soon)", font=("Arial", 12))
        self.reports_label.pack(pady=20)

    def upload_file(self):
        """Placeholder for uploading a CSV file."""
        messagebox.showinfo("Upload", "Upload functionality will be implemented in the next step.")

    def filter_transactions(self):
        """Placeholder for filtering transactions."""
        messagebox.showinfo("Filter", "Filter functionality will be implemented in the next step.")

    def prev_page(self):
        """Placeholder for previous page navigation."""
        messagebox.showinfo("Pagination", "Previous page functionality will be implemented in the next step.")

    def next_page(self):
        """Placeholder for next page navigation."""
        messagebox.showinfo("Pagination", "Next page functionality will be implemented in the next step.")

    def run_anomaly_detection(self):
        """Placeholder for running anomaly detection."""
        messagebox.showinfo("Anomaly Detection", "Anomaly detection functionality will be implemented in the next step.")

    def export_anomalies(self):
        """Placeholder for exporting anomalies to CSV."""
        messagebox.showinfo("Export", "Export functionality will be implemented in the next step.")

if __name__ == "__main__":
    root = tk.Tk()
    app = WatchdogAIUI(root)
    root.mainloop()