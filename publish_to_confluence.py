       
#!/usr/bin/env python3
"""
Automated Confluence Report Publisher
Runs the benchmark, collects output directory, and publishes results to Confluence.
"""
import subprocess
import sys
import os
from turtle import title
from atlassian import Confluence
from datetime import datetime
from pptx import Presentation

# --- CONFIGURATION ---
CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL", "https://milestone.atlassian.net/wiki")
USERNAME = os.environ.get("CONFLUENCE_USER", "loab@milestone.dk")
API_TOKEN = os.environ.get("CONFLUENCE_TOKEN", "")
SPACE_KEY = os.environ.get("CONFLUENCE_SPACE", "EACA")
MAIN_PAGE_TITLE = os.environ.get("CONFLUENCE_MAIN_PAGE", "FFMpeg Main Dashboard")
GITHUB_COMMIT_URL = os.environ.get("GITHUB_COMMIT_URL", "")


class ConfluenceReportGenerator:
    def __init__(self, confluence_url, username, api_token, space_key):
        self.confluence = Confluence(
            url=confluence_url,
            username=username,
            password=api_token
        )
        self.space_key = space_key

    def create_detailed_report_page(self, results_dir, report_title, parent_id=None, git_commit_url=None):
        """
        Create a detailed report page for the given results_dir and report_title if it does not already exist.
        """
        print(f"[DEBUG] git_commit_url in detailed report: {git_commit_url}")
        # Check if a child page with the same title exists under the dashboard
        if parent_id:
            children = self.confluence.get_child_pages(parent_id)
            for child in children:
                if child['title'] == report_title:
                    print(f"[INFO] Deleting existing detailed report page '{report_title}' under dashboard.")
                    self.confluence.remove_page(child['id'])
                    break
        # Otherwise, create the page as a child of the dashboard if parent_id is given
        create_kwargs = dict(space=self.space_key, title=report_title, body="<p>Uploading attachments...</p>", representation="storage")
        if parent_id:
            create_kwargs['parent_id'] = parent_id
        new_page = self.confluence.create_page(**create_kwargs)
        page_id = new_page['id']
        plots_dir = os.path.join(results_dir, "plots")
        vtune_dir = os.path.join(results_dir, "vtune_results")
        # Attach mv_comparison_result.txt and call_tree.html if present before other files
        mv_cmp_path = os.path.join(os.path.dirname(plots_dir), "mv_comparison_result.txt")
        if os.path.isfile(mv_cmp_path):
            self.confluence.attach_file(filename=mv_cmp_path, page_id=page_id, name="mv_comparison_result.txt")
        calltree_path = os.path.join(vtune_dir, "call_tree.html") if vtune_dir else None
        if calltree_path and os.path.isfile(calltree_path):
            self.confluence.attach_file(filename=calltree_path, page_id=page_id, name="call_tree.html")
        self.attach_detailed_report_files(page_id, plots_dir, vtune_dir)
        # Compose the detailed report body referencing attachments
        body = self.generate_detailed_report_body(plots_dir, vtune_dir, page_id, git_commit_url=git_commit_url)
        page_info = self.confluence.get_page_by_id(page_id, expand='version')
        version_number = page_info['version']['number'] + 1
        update_data = {
            'id': page_id,
            'type': 'page',
            'title': report_title,
            'space': {'key': self.space_key},
            'body': {
                'storage': {
                    'value': body,
                    'representation': 'storage'
                }
            },
            'version': {'number': version_number},
            'metadata': {
                'properties': {
                    'content-appearance-draft': {'value': 'full-width'},
                    'content-appearance-published': {'value': 'full-width'}
                }
            }
        }
        print("[DEBUG] Detailed report body being sent to Confluence:\n" + body[:2000] + ("..." if len(body) > 2000 else ""))
        self.confluence.put(f'/rest/api/content/{page_id}', data=update_data)
        print(f"[INFO] Created detailed report page '{report_title}' (id={page_id})")
        return page_id
        
    def generate_detailed_report(self, confluence, page_id, results_dir, attachments, call_tree_html, call_tree_list_html, mv_comparison, detailed_report_title, is_first_run, git_commit_url=None):
        version_number = page_info['version']['number'] + 1
        update_data = {
            'id': page_id,
            'type': 'page',
            'title': report_title,
            'space': {'key': self.space_key},
            'body': {
                'storage': {
                    'value': body,
                    'representation': 'storage'
                }
            },
            'version': {'number': version_number},
            'metadata': {
                'properties': {
                    'content-appearance-draft': {'value': 'full-width'},
                    'content-appearance-published': {'value': 'full-width'}
                }
            }
        }
        self.confluence.put(f'/rest/api/content/{page_id}', data=update_data)
        print(f"[INFO] Created detailed report page '{report_title}' (id={page_id})")
        return page_id

    def set_full_width(self, page_id):
        """
        Set the Confluence page to full-width appearance using REST API (with required version).
        """
        try:
            # Get current version
            page_info = self.confluence.get_page_by_id(page_id, expand='version')
            version_number = page_info['version']['number']
            payload = {"value": "full-width", "version": {"number": version_number}}
            url = f"/rest/api/content/{page_id}/property/content-appearance-draft"
            self.confluence.put(url, data=payload)
            url2 = f"/rest/api/content/{page_id}/property/content-appearance-published"
            self.confluence.put(url2, data=payload)
        except Exception as e:
            print(f"[WARN] Could not set full-width appearance: {e}")

    def attach_detailed_report_files(self, page_id, plots_dir, vtune_dir):
        """
        Attach all relevant images/files for the detailed report to the given page_id.
        """
        import glob
        # Profiler Results (VTune Hotspots)
        vtune_img = os.path.join(vtune_dir, "vtune_hotspots.png") if vtune_dir else None
        if vtune_img and os.path.exists(vtune_img):
            self.confluence.attach_file(filename=vtune_img, page_id=page_id, name="vtune_hotspots.png")
        # VTune Call Tree HTML
        calltree_html = os.path.join(vtune_dir, "call_tree.html") if vtune_dir else None
        if calltree_html and os.path.exists(calltree_html):
            self.confluence.attach_file(filename=calltree_html, page_id=page_id, name="call_tree.html")
        # Fastest Methods Table
        fastest_img = os.path.join(plots_dir, "fastest_high_profile_methods.png")
        if os.path.exists(fastest_img):
            self.confluence.attach_file(filename=fastest_img, page_id=page_id, name="fastest_high_profile_methods.png")
        # Scaling charts
        scaling = [
            "scaling_fps.png",
            "scaling_timeperframe.png",
            "scaling_cpu.png",
            "scaling_memory.png"
        ]
        for fname in scaling:
            img_path = os.path.join(plots_dir, fname)
            if os.path.exists(img_path):
                self.confluence.attach_file(filename=img_path, page_id=page_id, name=fname)
        # Grouped Bar Charts
        grouped = [
            "grouped_barchart_fps.png",
            "grouped_barchart_timeperframe.png",
            "grouped_barchart_cpu.png",
            "grouped_barchart_memory.png"
        ]
        for fname in grouped:
            img_path = os.path.join(plots_dir, fname)
            if os.path.exists(img_path):
                self.confluence.attach_file(filename=img_path, page_id=page_id, name=fname)
        # Detailed Tables per Streams Count
        for img in sorted(glob.glob(os.path.join(plots_dir, "detail_table_*streams.png"))):
            self.confluence.attach_file(filename=img, page_id=page_id, name=os.path.basename(img))

    def generate_detailed_report_body(self, plots_dir, vtune_dir, page_id=None, git_commit_url=None):
        """
        Generate the detailed report body using the slide structure and images from plots_dir and vtune_dir.
        """
        import glob
        import requests
        

        # Helper to embed HTML call tree if available (interactive)
        def get_calltree_html():
            if not page_id:
                return ""

            try:
                attachments = self.confluence.get_attachments_from_content(page_id, filename="call_tree.html")
                att = attachments['results'][0] if attachments['size'] > 0 else None
                if att and 'download' in att['_links']:
                    url = self.confluence.url + att['_links']['download']
                    resp = requests.get(url, auth=(self.confluence.username, self.confluence.password))
                    if resp.ok:
                        return f'<ac:structured-macro ac:name="html"><ac:plain-text-body><![CDATA[{resp.text}]]></ac:plain-text-body></ac:structured-macro>'
            except Exception:
                pass
            return "<em>No call tree HTML available</em>"
        
        def get_mv_cmp_attachment():
            if not page_id:
                return "<em>No motion vector comparison result available</em>"
            try:
                attachments = self.confluence.get_attachments_from_content(page_id, filename="mv_comparison_result.txt")
                att = attachments['results'][0] if attachments['size'] > 0 else None
                if att and 'download' in att['_links']:
                    url = self.confluence.url + att['_links']['download']
                    import requests
                    resp = requests.get(url, auth=(self.confluence.username, self.confluence.password))
                    if resp.ok and resp.text.strip():
                        return f'<pre style="background:#f4f4f4; border:1px solid #ccc; padding:10px;">{resp.text.strip()}</pre>'
            except Exception:
                pass
            return "<em>No motion vector comparison result available</em>"

        # Helper to embed call tree as plain text (non-interactive)
        def get_calltree_pre():
            if not page_id:
                return ""
            try:
                attachments = self.confluence.get_attachments_from_content(page_id, filename="call_tree.html")
                att = attachments['results'][0] if attachments['size'] > 0 else None
                if att and 'download' in att['_links']:
                    url = self.confluence.url + att['_links']['download']
                    resp = requests.get(url, auth=(self.confluence.username, self.confluence.password))
                    if resp.ok and resp.text.strip():
                        html_content = resp.text.strip()
                        try:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(html_content, 'html.parser')
                            ul = soup.find('ul', class_='vtune-tree')
                            def extract_plain(node):
                                items = []
                                for li in node.find_all('li', recursive=False):
                                    func = li.find('span', class_='func')
                                    percent = li.find('span', class_='percent')
                                    self_time = li.find('span', class_='self')
                                    label = ''
                                    if func:
                                        label += func.get_text(strip=True)
                                    if percent:
                                        label += f' {percent.get_text(strip=True)}'
                                    if self_time:
                                        label += f' {self_time.get_text(strip=True)}'
                                    child_ul = li.find('ul')
                                    if child_ul:
                                        items.append(f'<li>{label}<ul>{extract_plain(child_ul)}</ul></li>')
                                    else:
                                        items.append(f'<li>{label}</li>')
                                return ''.join(items)
                            if ul:
                                tree_html = f'<ul>{extract_plain(ul)}</ul>'
                                return f'<div style="background:#f4f4f4; border:1px solid #ccc; padding:10px; width:100%; max-width:100vw; overflow-x:auto;">{tree_html}</div>'
                            # If no <ul>, try to parse <table> as a call tree
                            table = soup.find('table')
                            if table:
                                rows = table.find_all('tr')
                                headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(['th','td'])]
                                fn_idx = next((i for i, h in enumerate(headers) if 'function' in h), 0)
                                percent_idx = next((i for i, h in enumerate(headers) if 'cpu total' in h or 'percent' in h), 1)
                                self_idx = next((i for i, h in enumerate(headers) if 'self' in h), 2)
                                items = []
                                stack = [(0, items)]  # (indent, list)
                                for row in rows[1:]:
                                    cols = row.find_all(['td','th'])
                                    if not cols: continue
                                    fn_cell = cols[fn_idx]
                                    # Count indentation: leading &nbsp;, spaces, or triangles
                                    raw_html = str(fn_cell)
                                    nbsp_count = raw_html.count('&nbsp;')
                                    text = fn_cell.get_text()
                                    triangle_count = text.count('\u25b6') + text.count('▶')
                                    space_count = 0
                                    for c in text:
                                        if c == ' ':
                                            space_count += 1
                                        else:
                                            break
                                    indent = nbsp_count + triangle_count + (space_count // 2)
                                    label = text.strip()
                                    if percent_idx < len(cols):
                                        label += f' {cols[percent_idx].get_text(strip=True)}'
                                    if self_idx < len(cols):
                                        label += f' {cols[self_idx].get_text(strip=True)}'
                                    # Manage stack for nesting
                                    while stack and indent < stack[-1][0]:
                                        stack.pop()
                                    parent_list = stack[-1][1]
                                    new_list = []
                                    parent_list.append(f'<li>{label}')
                                    # Look ahead to next row to see if it is more indented
                                    next_indent = None
                                    if row != rows[-1]:
                                        next_row = rows[rows.index(row)+1]
                                        next_cols = next_row.find_all(['td','th'])
                                        if next_cols:
                                            next_raw_html = str(next_cols[fn_idx])
                                            next_nbsp_count = next_raw_html.count('&nbsp;')
                                            next_text = next_cols[fn_idx].get_text()
                                            next_triangle_count = next_text.count('\u25b6') + next_text.count('▶')
                                            next_space_count = 0
                                            for c in next_text:
                                                if c == ' ':
                                                    next_space_count += 1
                                                else:
                                                    break
                                            next_indent = next_nbsp_count + next_triangle_count + (next_space_count // 2)
                                    if next_indent is not None and next_indent > indent:
                                        parent_list.append('<ul>')
                                        stack.append((next_indent, parent_list))
                                    else:
                                        parent_list.append('</li>')
                                # Close any open <ul>
                                while len(stack) > 1:
                                    stack.pop()
                                    stack[-1][1].append('</ul></li>')
                                tree_html = f'<ul>{"".join(items)}</ul>'
                                return f'<div style="background:#f4f4f4; border:1px solid #ccc; padding:10px; width:100%; max-width:100vw; overflow-x:auto;">{tree_html}</div>'
                            # fallback: just show text
                            return f'<pre style="background:#f4f4f4; border:1px solid #ccc; padding:10px; width:100%; max-width:100vw; overflow-x:auto;">{soup.get_text()}</pre>'
                        except Exception as e:
                            return f'<pre style="background:#f4f4f4; border:1px solid #ccc; padding:10px; width:100%; max-width:100vw; overflow-x:auto;">{html_content}</pre>'
                        content += "<h3>Profiler Results</h3>\n"
                        # Add interactive call tree view using the Confluence HTML macro plugin
                        content += "<h4>Call Tree (Interactive)</h4>\n"
                        # Embed the HTML macro for the interactive call tree
                        content += f'<ac:structured-macro ac:name="html"><ac:plain-text-body><![CDATA[{call_tree_html}]]></ac:plain-text-body></ac:structured-macro>\n'
                        # Add non-interactive call tree view
                        content += "<h4>Call Tree (Plain List)</h4>\n"
                        content += call_tree_list_html
                        # Add motion vector comparison
                        content += "<h3>Motion Vector Comparison</h3>\n"
                        content += f"<pre>{mv_comparison}</pre>\n"
                        return content
                    resp = requests.get(url, auth=(self.confluence.username, self.confluence.password))
                    print(f"[DEBUG] mv_comparison_result.txt content: {resp.text[:200]} ...")
                    if resp.ok and resp.text.strip():
                        return f'<pre style="background:#f4f4f4; border:1px solid #ccc; padding:10px; width:100%; max-width:100vw; overflow-x:auto;">{resp.text.strip()}</pre>'
            except Exception as e:
                print(f"[DEBUG] Error reading mv_comparison_result.txt: {e}")
            return "<em>No motion vector comparison result available</em>"
        
        

        body = '<div style="text-align: left; width: 100vw; max-width: 100vw; margin: 0; padding: 0;">'
        # 1. Motion Vector Comparison (always first)
        mv_cmp = get_mv_cmp_attachment()
        body += '<h3>Motion Vector Comparison (Frames 10-100)</h3>'
        body += mv_cmp

        print(f"[DEBUG] git_commit_url in detailed report: {git_commit_url}")

        if git_commit_url:
            body += '<h3>Git Commit Url</h3>'
            body += f'<a href="{git_commit_url}" style="font-size:1.1em;color:#1976d2;">{git_commit_url}</a></div>'

        # 2. Profiler Results (VTune Hotspots)
        vtune_img = os.path.join(vtune_dir, "vtune_hotspots.png") if vtune_dir else None
        if vtune_img and os.path.exists(vtune_img):
            body += '<h3>Profiler Results</h3>'
            body += '<ac:image ac:thumbnail="true" ac:width="600"><ri:attachment ri:filename="vtune_hotspots.png" /></ac:image>'
        # 3. VTune Call Tree HTML (interactive and non-interactive, always after profiler)
        # Interactive: as before
        calltree_html = get_calltree_html()
        body += '<h3>VTune Call Tree (Interactive)</h3>'
        body += calltree_html
        # Non-Interactive: new logic
        def get_attachment_content(page_id, filename):
            try:
                attachments = self.confluence.get_attachments_from_content(page_id, filename=filename)
                att = attachments['results'][0] if attachments['size'] > 0 else None
                if att and 'download' in att['_links']:
                    import requests
                    url = self.confluence.url + att['_links']['download']
                    resp = requests.get(url, auth=(self.confluence.username, self.confluence.password))
                    if resp.ok:
                        return resp.text
            except Exception:
                pass
            return None

        calltree_content = get_attachment_content(page_id, "call_tree.html")
        body += '<h3>VTune Call Tree (Non-Interactive)</h3>'
        if calltree_content:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(calltree_content, 'html.parser')
                tree_container = soup.find('ul', class_='tree-root')
                if tree_container:
                    def extract_tree_text(ul_element, indent=0):
                        result = []
                        for li in ul_element.find_all('li', class_='tree-node', recursive=False):
                            name_span = li.find('span', class_='name')
                            cpu_total = li.find('span', class_='cpu-total')
                            cpu_self = li.find('span', class_='cpu-self')
                            if name_span:
                                line = '  ' * indent + name_span.get_text(strip=True)
                                if cpu_total:
                                    line += f' {cpu_total.get_text(strip=True)}'
                                if cpu_self:
                                    line += f' {cpu_self.get_text(strip=True)}'
                                result.append(line)
                            child_ul = li.find('ul', class_='children')
                            if child_ul:
                                result.extend(extract_tree_text(child_ul, indent + 1))
                        return result
                    tree_lines = extract_tree_text(tree_container)
                    tree_text = '\n'.join(tree_lines[:100])  # Limit to first 100 lines
                    body += f'<pre style="background:#f4f4f4; border:1px solid #ccc; padding:10px; max-height:400px; overflow-y:auto;">{tree_text}</pre>'
                else:
                    body += f'<pre style="background:#f4f4f4; border:1px solid #ccc; padding:10px;">{soup.get_text()[:2000]}</pre>'
            except Exception:
                body += f'<pre style="background:#f4f4f4; border:1px solid #ccc; padding:10px;">{calltree_content[:2000]}...</pre>'
        else:
            body += '<em>No call tree data available</em>'
        # Fastest Methods Table
        fastest_img = os.path.join(plots_dir, "fastest_high_profile_methods.png")
        if os.path.exists(fastest_img):
            body += '<h3>Fastest Methods</h3>'
            body += '<ac:image ac:thumbnail="true" ac:width="600"><ri:attachment ri:filename="fastest_high_profile_methods.png" /></ac:image>'
        # Scaling charts
        scaling = [
            ("Throughput Scaling", "scaling_fps.png"),
            ("Latency Scaling", "scaling_timeperframe.png"),
            ("CPU Usage Scaling", "scaling_cpu.png"),
            ("Memory Usage Scaling", "scaling_memory.png")
        ]
        for title, fname in scaling:
            img_path = os.path.join(plots_dir, fname)
            if os.path.exists(img_path):
                body += f'<h3>{title}</h3>'
                body += f'<ac:image ac:thumbnail="true" ac:width="600"><ri:attachment ri:filename="{fname}" /></ac:image>'
        # Grouped Bar Charts
        grouped = [
            ("Grouped FPS Comparison (All Streams)", "grouped_barchart_fps.png"),
            ("Grouped Latency Comparison (All Streams)", "grouped_barchart_timeperframe.png"),
            ("Grouped CPU Usage Comparison (All Streams)", "grouped_barchart_cpu.png"),
            ("Grouped Memory Usage Comparison (All Streams)", "grouped_barchart_memory.png")
        ]
        for title, fname in grouped:
            img_path = os.path.join(plots_dir, fname)
            if os.path.exists(img_path):
                body += f'<h3>{title}</h3>'
                body += f'<ac:image ac:thumbnail="true" ac:width="600"><ri:attachment ri:filename="{fname}" /></ac:image>'
        # Detailed Tables per Streams Count
        for img in sorted(glob.glob(os.path.join(plots_dir, "detail_table_*streams.png"))):
            streams = os.path.basename(img).split('_')[2].replace('streams.png','')
            body += f'<h3>Performance Table: Streams={streams}</h3>'
            body += f'<ac:image ac:thumbnail="true" ac:width="600"><ri:attachment ri:filename="{os.path.basename(img)}" /></ac:image>'
    # (Removed: Only use git_commit_url at the top)
        body += '</div>'
        return body

    def update_main_dashboard_summary(self, first_results_dir, latest_results_dir, report_title, git_commit_run1=None, git_commit_run2=None):
        dashboard_page = self.confluence.get_page_by_title(self.space_key, MAIN_PAGE_TITLE)
        if not dashboard_page:
            raise Exception(f"Main dashboard page '{MAIN_PAGE_TITLE}' not found.")
        dashboard_id = dashboard_page['id']
        import os, glob, time
        page_body = f'<div style="text-align: left; width: 100vw; max-width: 100vw; margin: 0; padding: 0;">'
        files_to_attach = []
        def add_if_exists(path, name):
            if path and os.path.isfile(path):
                files_to_attach.append((path, name))
        if first_results_dir:
            plots_first = os.path.join(first_results_dir, "plots")
            vtune_dir_first = os.path.join(first_results_dir, "vtune_results")
            add_if_exists(os.path.join(plots_first, "detail_table_5streams_highlighted.png"), "detail_table_5streams_highlighted.png")
            add_if_exists(os.path.join(plots_first, "grouped_barchart_cpu.png"), "grouped_barchart_cpu.png")
            add_if_exists(os.path.join(plots_first, "grouped_barchart_memory.png"), "grouped_barchart_memory.png")
            add_if_exists(os.path.join(vtune_dir_first, "vtune_hotspots.png"), "vtune_hotspots.png")
            # Attach mv_comparison_result.txt and call_tree.html from first run with unique names
            mv_cmp_first_path = os.path.join(first_results_dir, "mv_comparison_result.txt")
            if os.path.isfile(mv_cmp_first_path):
                files_to_attach.append((mv_cmp_first_path, "mv_comparison_result_first.txt"))
            calltree_first_path = os.path.join(vtune_dir_first, "call_tree.html")
            if os.path.isfile(calltree_first_path):
                files_to_attach.append((calltree_first_path, "call_tree_first.html"))
        if latest_results_dir:
            plots_latest = os.path.join(latest_results_dir, "plots")
            vtune_dir_latest = os.path.join(latest_results_dir, "vtune_results")
            # Attach latest run's files with 'current_' prefix to avoid collision
            detail_latest_path = os.path.join(plots_latest, "detail_table_5streams_highlighted.png")
            if os.path.isfile(detail_latest_path):
                files_to_attach.append((detail_latest_path, "current_detail_table_5streams_highlighted.png"))
            cpu_latest_path = os.path.join(plots_latest, "grouped_barchart_cpu.png")
            if os.path.isfile(cpu_latest_path):
                files_to_attach.append((cpu_latest_path, "current_grouped_barchart_cpu.png"))
            mem_latest_path = os.path.join(plots_latest, "grouped_barchart_memory.png")
            if os.path.isfile(mem_latest_path):
                files_to_attach.append((mem_latest_path, "current_grouped_barchart_memory.png"))
            add_if_exists(os.path.join(vtune_dir_latest, "vtune_hotspots.png"), "current_vtune_hotspots.png")
            # Attach mv_comparison_result.txt and call_tree.html from latest run with unique names
            mv_cmp_latest_path = os.path.join(latest_results_dir, "mv_comparison_result.txt")
            if os.path.isfile(mv_cmp_latest_path):
                files_to_attach.append((mv_cmp_latest_path, "mv_comparison_result.txt"))
            calltree_latest_path = os.path.join(vtune_dir_latest, "call_tree.html")
            if os.path.isfile(calltree_latest_path):
                files_to_attach.append((calltree_latest_path, "call_tree.html"))
            add_if_exists(os.path.join(latest_results_dir, "decoded_output.mp4"), "decoded_output.mp4")
        for fpath, fname in files_to_attach:
            print(f"[DEBUG] Attaching file: {fpath} as {fname} to dashboard {dashboard_id}")
            try:
                self.confluence.attach_file(filename=fpath, page_id=dashboard_id, name=fname)
            except Exception as e:
                print(f"[ERROR] Failed to attach {fname} to dashboard: {e}")
        time.sleep(5)
        def get_img_tag(fname):
            return f'<ac:image ac:thumbnail="true" ac:width="450"><ri:attachment ri:filename="{fname}" /></ac:image>'
        def get_calltree_html():
            try:
                att = self.confluence.get_attachment_by_file_name(dashboard_id, "call_tree.html")
                if att and 'download' in att['_links']:
                    import requests
                    url = self.confluence.url + att['_links']['download']
                    resp = requests.get(url, auth=(self.confluence.username, self.confluence.password))
                    if resp.ok:
                        return f'<ac:structured-macro ac:name="html"><ac:plain-text-body><![CDATA[{resp.text}]]></ac:plain-text-body></ac:structured-macro>'
            except Exception:
                pass
            return "<em>No data available</em>"
        def get_mv_cmp_attachment(name):
            try:
                attachments = self.confluence.get_attachments_from_content(dashboard_id, filename=name)
                att = attachments['results'][0] if attachments['size'] > 0 else None
                if att and 'download' in att['_links']:
                    import requests
                    url = self.confluence.url + att['_links']['download']
                    resp = requests.get(url, auth=(self.confluence.username, self.confluence.password))
                    if resp.ok and resp.text.strip():
                        return f'<pre style="background:#f4f4f4; border:1px solid #ccc; padding:10px;">{resp.text.strip()}</pre>'
            except Exception:
                pass
            return "<em>No data available</em>"


        # 1. Motion Vector Comparison
        page_body += '<h3>Motion Vector Comparison (Frames 10-100)</h3>'
        mv_first = get_mv_cmp_attachment("mv_comparison_result_first.txt")
        mv_latest = get_mv_cmp_attachment("mv_comparison_result.txt")
        page_body += '<table class="mv-mini-table"><tr><th>First Run</th><th>Latest Run</th></tr>'
        page_body += f'<tr><td>{mv_first}</td><td>{mv_latest}</td></tr></table>'

        # 2. VTune Hotspots
        page_body += '<h3>VTune Hotspots (Top 30)</h3>'
        img_first = get_img_tag("vtune_hotspots.png")
        img_latest = get_img_tag("current_vtune_hotspots.png")
        page_body += '<table class="mv-mini-table"><tr><th>First Run</th><th>Latest Run</th></tr>'
        page_body += f'<tr><td>{img_first}</td><td>{img_latest}</td></tr></table>'

        # 3. GitHub Commit (per run)
        page_body += '<h3>GitHub Commit</h3>'
        page_body += '<table class="mv-mini-table"><tr><th>First Run</th><th>Latest Run</th></tr>'
        page_body += '<tr>'
        if git_commit_run1:
            page_body += f'<td><a href="{git_commit_run1}" target="_blank">{git_commit_run1}</a></td>'
        else:
            page_body += '<td>N/A</td>'
        if git_commit_run2:
            page_body += f'<td><a href="{git_commit_run2}" target="_blank">{git_commit_run2}</a></td>'
        else:
            page_body += '<td>N/A</td>'
        page_body += '</tr></table>'

        # 4. VTune Call Tree (Interactive)
        def get_calltree_html(name):
            try:
                attachments = self.confluence.get_attachments_from_content(dashboard_id, filename=name)
                att = attachments['results'][0] if attachments['size'] > 0 else None
                if att and 'download' in att['_links']:
                    import requests
                    url = self.confluence.url + att['_links']['download']
                    resp = requests.get(url, auth=(self.confluence.username, self.confluence.password))
                    if resp.ok:
                        html = resp.text
                        macro = f'<ac:structured-macro ac:name="html"><ac:plain-text-body><![CDATA[{html}]]></ac:plain-text-body></ac:structured-macro>'
                        return macro if html.strip() else "<em>No call tree HTML available</em>"
            except Exception:
                pass
            return "<em>No call tree HTML available</em>"
        page_body += '<h3>VTune Call Tree (Interactive)</h3>'
        calltree_first = get_calltree_html("call_tree_first.html")
        calltree_latest = get_calltree_html("call_tree.html")
        page_body += '<table class="mv-mini-table"><tr><th>First Run</th><th>Latest Run</th></tr>'
        page_body += f'<tr><td>{calltree_first}</td><td>{calltree_latest}</td></tr></table>'

        # 5. Detailed Table
        page_body += '<h3>Detailed Table</h3>'
        table_first = get_img_tag("detail_table_1streams_highlighted.png")
        table_latest = get_img_tag("current_detail_table_1streams_highlighted.png")
        page_body += '<table class="mv-mini-table"><tr><th>First Run</th><th>Latest Run</th></tr>'
        page_body += f'<tr><td>{table_first}</td><td>{table_latest}</td></tr></table>'

        # 6. Grouped CPU Usage
        page_body += '<h3>Grouped CPU Usage (All Streams)</h3>'
        cpu_first = get_img_tag("grouped_barchart_cpu.png")
        cpu_latest = get_img_tag("current_grouped_barchart_cpu.png")
        page_body += '<table class="mv-mini-table"><tr><th>First Run</th><th>Latest Run</th></tr>'
        page_body += f'<tr><td>{cpu_first}</td><td>{cpu_latest}</td></tr></table>'

        # 7. Grouped Memory Usage
        page_body += '<h3>Grouped Memory Usage (All Streams)</h3>'
        mem_first = get_img_tag("grouped_barchart_memory.png")
        mem_latest = get_img_tag("current_grouped_barchart_memory.png")
        page_body += '<table class="mv-mini-table"><tr><th>First Run</th><th>Latest Run</th></tr>'
        page_body += f'<tr><td>{mem_first}</td><td>{mem_latest}</td></tr></table>'

        # 9. Detailed Reports (link to both runs if available)
        page_body += '<h3>Detailed Reports</h3>'
        page_body += '<ul>'
        import re
        if first_results_dir:
            first_dir = os.path.basename(first_results_dir.rstrip('/'))
            m1 = re.search(r'(\d{8})_(\d{6})', first_dir)
            if m1:
                date_str = m1.group(1)
                time_str = m1.group(2)
                first_report_title = f"Automated Report: {date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
            else:
                first_report_title = f"Automated Report: {first_dir}"
            page_body += f'<li><b>First Run:</b> <ac:link><ri:page ri:content-title="{first_report_title}" /></ac:link></li>'
        page_body += f'<li><b>Latest Run:</b> <ac:link><ri:page ri:content-title="{report_title}" /></ac:link></li>'
        page_body += '</ul>'
        page_body += '</div>'
        try:
            print(f"[DEBUG] Updating dashboard page {dashboard_id} with summary body...")
            page_info = self.confluence.get_page_by_id(dashboard_id, expand='version')
            version_number = page_info['version']['number'] + 1
            update_data = {
                'id': dashboard_id,
                'type': 'page',
                'title': MAIN_PAGE_TITLE,
                'space': {'key': self.space_key},
                'body': {
                    'storage': {
                        'value': page_body,
                        'representation': 'storage'
                    }
                },
                'version': {'number': version_number},
                'metadata': {
                    'properties': {
                        'content-appearance-draft': {'value': 'full-width'},
                        'content-appearance-published': {'value': 'full-width'}
                    }
                }
            }
            self.confluence.put(f'/rest/api/content/{dashboard_id}', data=update_data)
            print(f"[DEBUG] Dashboard page update complete.")
        except Exception as e:
            print(f"[ERROR] Failed to update dashboard page: {e}")

def cli():
    print("[DEBUG] Entered cli() function.")
    import argparse

    parser = argparse.ArgumentParser(description="Publish benchmark results to Confluence.")
    parser.add_argument('first_results_dir', help='Results directory for the first run (left column)')
    parser.add_argument('latest_results_dir', help='Results directory for the latest run (right column)')
    parser.add_argument('git_commit_run1', help='Git commit hash or URL for run 1 (first run)')
    parser.add_argument('git_commit_run2', help='Git commit hash or URL for run 2 (latest run)')
    args = parser.parse_args()

    generator = ConfluenceReportGenerator(CONFLUENCE_URL, USERNAME, API_TOKEN, SPACE_KEY)
    print("[DEBUG] ConfluenceReportGenerator initialized.")

    # Infer report title from latest_results_dir (e.g., 'Automated Report: 2025-09-17 20:16:54')
    import re
    import os
    latest_dir = args.latest_results_dir.rstrip('/')
    m = re.search(r'(\d{8})_(\d{6})', os.path.basename(latest_dir))
    if m:
        date_str = m.group(1)
        time_str = m.group(2)
        report_title = f"Automated Report: {date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
    else:
        report_title = f"Automated Report: {os.path.basename(latest_dir)}"


    # Get dashboard page id to use as parent
    dashboard_page = generator.confluence.get_page_by_title(SPACE_KEY, MAIN_PAGE_TITLE)
    print("[DEBUG] Got dashboard page.")
    if not dashboard_page:
        print(f"[ERROR] Main dashboard page '{MAIN_PAGE_TITLE}' not found.")
        raise Exception(f"Main dashboard page '{MAIN_PAGE_TITLE}' not found.")
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
    print("✅ Dashboard summary updated.")


if __name__ == "__main__":
    cli()
