       
#!/usr/bin/env python3
"""
Automated Confluence Report Publisher
Runs the benchmark, collects output directory, and publishes results to Confluence.
"""
import os
import argparse
import re

from dotenv import load_dotenv
load_dotenv('.env')
        
import confluence_report_generator as conf

def cli():
    confluence_url = os.environ.get("CONFLUENCE_URL")
    space_key = os.environ.get("SPACE_KEY")
    main_page_title = os.environ.get("MAIN_PAGE_TITLE")
    username = os.environ.get("CONFLUENCE_USER")
    api_token = os.environ.get("CONFLUENCE_TOKEN")

    print("[DEBUG] Entered cli() function.")

    parser = argparse.ArgumentParser(description="Publish benchmark results to Confluence.")
    parser.add_argument('first_results_dir', help='Results directory for the first run (left column)')
    parser.add_argument('latest_results_dir', help='Results directory for the latest run (right column)')
    parser.add_argument('git_commit_run1', help='Git commit hash or URL for run 1 (first run)')
    parser.add_argument('git_commit_run2', help='Git commit hash or URL for run 2 (latest run)')
    args = parser.parse_args()

    generator = conf.ConfluenceReportGenerator(confluence_url, username, api_token, space_key, main_page_title)
    print("[DEBUG] ConfluenceReportGenerator initialized.")

    # Infer report title from latest_results_dir (e.g., 'Automated Report: 2025-09-17 20:16:54')
    latest_dir = args.latest_results_dir.rstrip('/')
    m = re.search(r'(\d{8})_(\d{6})', os.path.basename(latest_dir))
    if m:
        date_str = m.group(1)
        time_str = m.group(2)
        report_title = f"Automated Report: {date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
    else:
        report_title = f"Automated Report: {os.path.basename(latest_dir)}"


    # Get dashboard page id to use as parent
    dashboard_page = generator.get_page_by_title()
    print("[DEBUG] Got dashboard page.")
    if not dashboard_page:
        print(f"[ERROR] Main dashboard page '{main_page_title}' not found.")
        raise Exception(f"Main dashboard page '{main_page_title}' not found.")
    dashboard_id = dashboard_page['id']
    print(f"[DEBUG] Dashboard ID: {dashboard_id}")

    # Debug and check existence for first run (first argument)
    first_dir = args.first_results_dir.rstrip('/')
    print(f"[DEBUG] First results dir: {first_dir}")
    if not os.path.isdir(first_dir):
        print(f"[ERROR] First results directory does not exist: {first_dir}")
    else:
        m1 = re.search(r'(\d{8})_(\d{6})', os.path.basename(first_dir))
        if m1:
            date_str = m1.group(1)
            time_str = m1.group(2)
            first_report_title = f"Automated Report: {date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
        else:
            first_report_title = f"Automated Report: {os.path.basename(first_dir)}"
        print(f"[DEBUG] Creating detailed report for first run: {first_report_title}")
        generator.create_detailed_report_page(first_dir, first_report_title, parent_id=dashboard_id, git_commit_url=args.git_commit_run1)
        print("[DEBUG] Finished creating detailed report for first run.")

    # Debug and check existence for latest run (second argument)
    latest_dir = args.latest_results_dir.rstrip('/')
    print(f"[DEBUG] Latest results dir: {latest_dir}")
    if not os.path.isdir(latest_dir):
        print(f"[ERROR] Latest results directory does not exist: {latest_dir}")
    else:
        m = re.search(r'(\d{8})_(\d{6})', os.path.basename(latest_dir))
        if m:
            date_str = m.group(1)
            time_str = m.group(2)
            report_title = f"Automated Report: {date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
        else:
            report_title = f"Automated Report: {os.path.basename(latest_dir)}"
        print(f"[DEBUG] Creating detailed report for latest run: {report_title}")
        generator.create_detailed_report_page(latest_dir, report_title, parent_id=dashboard_id, git_commit_url=args.git_commit_run2)
        print("[DEBUG] Finished creating detailed report for latest run.")

    # Always update dashboard summary
    print("[DEBUG] Updating dashboard summary...")
    generator.update_main_dashboard_summary(
        first_results_dir=args.first_results_dir,
        latest_results_dir=args.latest_results_dir,
        report_title=report_title,
        git_commit_run1=args.git_commit_run1,
        git_commit_run2=args.git_commit_run2
    )
    print("Dashboard summary updated.")


if __name__ == "__main__":
    cli()
