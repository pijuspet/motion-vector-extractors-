import pandas as pd
import sys
import os
import matplotlib.pyplot as plt

def build_vtune_tree(csv_file):
    """Build proper hierarchical tree from VTune CSV indentation"""
    df = pd.read_csv(csv_file, delimiter='\t')
    
    # Clean data
    df['CPU Time:Total'] = pd.to_numeric(df['CPU Time:Total'], errors='coerce').fillna(0)
    df['CPU Time:Self'] = pd.to_numeric(df['CPU Time:Self'], errors='coerce').fillna(0)
    
    nodes = {}
    stack = []  # Stack of (level, node_id) pairs
    roots = []
    
    for idx, row in df.iterrows():
        func_line = row['Function Stack']
        cpu_total = float(row['CPU Time:Total'])
        cpu_self = float(row['CPU Time:Self'])
        
        # Calculate indentation level
        leading_spaces = len(func_line) - len(func_line.lstrip(' '))
        level = leading_spaces // 2
        func_name = func_line.strip()
        
        # Create unique node ID
        node_id = f"node_{idx}"
        
        # Pop stack to current level
        while stack and stack[-1][0] >= level:
            stack.pop()
        
        # Get parent
        parent_id = stack[-1][1] if stack else None
        
        # Create node
        nodes[node_id] = {
            'name': func_name,
            'cpu_total': cpu_total,
            'cpu_self': cpu_self,
            'level': level,
            'children': [],
            'parent': parent_id
        }
        
        # Add to parent's children or roots
        if parent_id:
            nodes[parent_id]['children'].append(node_id)
        else:
            roots.append(node_id)
        
        # Push current node to stack
        stack.append((level, node_id))
    
    return nodes, roots

def generate_tree_html(nodes, node_id):
    """Generate properly nested HTML tree"""
    node = nodes[node_id]
    children = node['children']
    has_children = len(children) > 0
    
    # Generate the list item
    arrow = '▶' if has_children else ''
    collapsed_class = 'collapsed' if has_children else ''
    
    html = f'<li class="tree-node {collapsed_class}" data-node="{node_id}">\n'
    html += f'  <span class="node-content" onclick="toggleNode(\'{node_id}\')">\n'
    html += f'    <span class="arrow">{arrow}</span>\n'
    html += f'    <span class="name">{node["name"]}</span>\n'
    html += f'    <span class="cpu-total">{node["cpu_total"]:.1f}%</span>\n'
    html += f'    <span class="cpu-self">{node["cpu_self"]:.1f}s</span>\n'
    html += f'  </span>\n'
    
    # Add children if they exist
    if has_children:
        html += f'  <ul class="children" id="children_{node_id}" style="display: none;">\n'
        for child_id in children:
            html += generate_tree_html(nodes, child_id)
        html += f'  </ul>\n'
    
    html += '</li>\n'
    return html

def generate_complete_html(nodes, roots, output_file):
    """Generate complete HTML file with working tree"""
    
    tree_html = ""
    for root_id in roots:
        tree_html += generate_tree_html(nodes, root_id)
    
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>VTune Call Tree</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        
        .container {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .stats {{
            background-color: #ecf0f1;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 16px;
        }}
        
        .header {{
            display: flex;
            align-items: center;
            margin-bottom: 16px;
            padding: 8px 12px;
            background-color: #34495e;
            color: white;
            border-radius: 4px;
            font-weight: bold;
        }}
        
        .header .name {{ flex: 1; }}
        .header .cpu-total {{ width: 80px; text-align: right; color: #f39c12; }}
        .header .cpu-self {{ width: 60px; text-align: right; color: #bdc3c7; }}
        
        ul.tree-root, ul.children {{
            list-style: none;
            margin: 0;
            padding: 0;
        }}
        
        ul.children {{
            padding-left: 20px;
            border-left: 1px solid #ddd;
            margin-left: 10px;
        }}
        
        .tree-node {{
            margin: 2px 0;
        }}
        
        .node-content {{
            display: flex;
            align-items: center;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.2s;
        }}
        
        .node-content:hover {{
            background-color: #f0f8ff;
        }}
        
        .arrow {{
            width: 16px;
            font-size: 12px;
            color: #666;
            margin-right: 6px;
            user-select: none;
        }}
        
        .name {{
            flex: 1;
            font-weight: 500;
            color: #2c3e50;
        }}
        
        .cpu-total {{
            width: 80px;
            text-align: right;
            font-weight: bold;
            color: #e74c3c;
        }}
        
        .cpu-self {{
            width: 60px;
            text-align: right;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>VTune Function Call Tree</h2>
        <div class="stats">
            <strong>Tree Statistics:</strong> {len(nodes)} total function calls, {len(roots)} root nodes
        </div>
        <div class="header">
            <span class="name">Function Name</span>
            <span class="cpu-total">CPU Total</span>
            <span class="cpu-self">CPU Self</span>
        </div>
        <ul class="tree-root">
            {tree_html}
        </ul>
    </div>
    
    <script>
        function toggleNode(nodeId) {{
            const childrenContainer = document.getElementById('children_' + nodeId);
            const arrow = document.querySelector(`[data-node="${{nodeId}}"] .arrow`);
            
            if (childrenContainer) {{
                if (childrenContainer.style.display === 'none') {{
                    // Expand
                    childrenContainer.style.display = 'block';
                    arrow.textContent = '▼';
                }} else {{
                    // Collapse
                    childrenContainer.style.display = 'none';
                    arrow.textContent = '▶';
                }}
            }}
        }}
    </script>
</body>
</html>'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

def generate_hotspots_chart(csv_file, output_dir):
    """Generate PNG bar chart of top hotspots"""
    df = pd.read_csv(csv_file, delimiter='\t')
    df['CPU Time:Total'] = pd.to_numeric(df['CPU Time:Total'], errors='coerce').fillna(0)
    
    # Remove 'Total' and get top functions
    df_filtered = df[df['Function Stack'].str.strip().str.lower() != 'total'].copy()
    df_filtered['Function Clean'] = df_filtered['Function Stack'].str.strip()
    df_grouped = df_filtered.groupby('Function Clean')['CPU Time:Total'].sum().reset_index()
    df_top = df_grouped.sort_values('CPU Time:Total', ascending=False).head(30)
    
    plt.figure(figsize=(14, 10))
    bars = plt.barh(df_top['Function Clean'], df_top['CPU Time:Total'], 
                    color='#2980b9', height=0.6)
    
    plt.xlabel('CPU Time (%)', fontsize=13, fontweight='bold')
    plt.title('Top 30 VTune Hotspots', fontsize=18, fontweight='bold', pad=15)
    plt.gca().invert_yaxis()
    plt.grid(axis='x', linestyle='--', alpha=0.4)
    
    for bar, value in zip(bars, df_top['CPU Time:Total']):
        plt.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f"{value:.1f}%", va='center', ha='left', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    png_file = os.path.join(output_dir, "vtune_hotspots.png")
    plt.savefig(png_file, dpi=140, bbox_inches='tight')
    plt.close()
    print(f"Hotspots bar chart saved to: {png_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python vtune_tree.py <topdown.csv>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    print("Building VTune call tree...")
    
    nodes, roots = build_vtune_tree(csv_file)
    print(f"Built tree with {len(nodes)} nodes and {len(roots)} root functions")
    
    output_dir = os.path.dirname(os.path.abspath(csv_file))
    html_file = os.path.join(output_dir, "call_tree.html")
    
    generate_complete_html(nodes, roots, html_file)
    generate_hotspots_chart(csv_file, output_dir)
    
    print(f"HTML call tree saved to: {html_file}")

if __name__ == "__main__":
    main()
