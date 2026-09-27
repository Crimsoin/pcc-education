# Applies PCC branding to the Education site. Safe to re-run (reuses existing File records).
# Run inside the backend container:  env/bin/python /tmp/pcc-branding/apply_branding.py
import os
import frappe

SITE = "portal.srv1586246.hstgr.cloud"
SRC = "/tmp/pcc-branding"
APP_NAME = "PCC Portal"
COMPANY = "Philippine Coding Camp"

frappe.init(site=SITE, sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")


def public_file(name):
	existing = frappe.db.get_value("File", {"file_name": name, "is_private": 0}, "file_url")
	if existing:
		return existing
	with open(os.path.join(SRC, name), "rb") as f:
		doc = frappe.get_doc({"doctype": "File", "file_name": name, "is_private": 0, "content": f.read()})
	doc.insert(ignore_permissions=True)
	return doc.file_url


logo = public_file("pcc-logo.png")
favicon = public_file("pcc-favicon.png")

ws = frappe.get_single("Website Settings")
ws.app_name = APP_NAME
ws.app_logo = logo
ws.favicon = favicon
ws.splash_image = logo
ws.brand_html = (
	f'<img src="{logo}" alt="PCC" style="height:28px;vertical-align:middle;margin-right:8px">'
	f"<span style=\"font-weight:700;vertical-align:middle\">{COMPANY}</span>"
)
ws.save()

nb = frappe.get_single("Navbar Settings")
nb.app_logo = logo
nb.save()

frappe.db.set_single_value("System Settings", "app_name", APP_NAME)

es = frappe.get_single("Education Settings")
es.school_college_name_abbreviation = "PCC"
es.school_college_logo = logo
es.save()

frappe.db.set_value("Company", COMPANY, "company_logo", logo)

frappe.db.commit()
frappe.clear_cache()
print("logo:", logo, "| favicon:", favicon, "| app name:", APP_NAME)
frappe.destroy()
