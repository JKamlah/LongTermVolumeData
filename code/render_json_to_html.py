import glob
import json
import os
import sys

from bs4 import BeautifulSoup


def load_and_accumulate_json_files(folder):
    accumulated_data = {"Provider": {}}

    # Dictionary to track how many times a provider has been encountered
    provider_counter = {}

    # Search for all JSON files matching *_data.json pattern
    json_files = glob.glob(os.path.join(folder, '**/*_data.json'), recursive=True)

    for json_file_path in json_files:
        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            try:
                data = json.load(json_file)
                if "Provider" in data:
                    # Merge provider data into accumulated dictionary
                    for provider_name, provider_data in data["Provider"].items():
                        if provider_name not in accumulated_data["Provider"]:
                            # If the provider doesn't exist, just add it
                            accumulated_data["Provider"][provider_name] = provider_data
                            provider_counter[provider_name] = 1  # Start counting
                        else:
                            # If the provider exists, we need to add a new layer with resource-Number
                            resource_number = provider_counter[provider_name] + 1
                            resource_name = f'Resource'
                            if resource_number == 2:
                                # Move the current data to 'Resource-1' and replace the rest of the dictionary
                                accumulated_data["Provider"][provider_name] = {
                                    f'{resource_name}-1': accumulated_data["Provider"][provider_name].copy()
                                }
                            resource_key = f'{resource_name}-{resource_number}'

                            # Add the provider's new resource under a new layer
                            if resource_key not in accumulated_data["Provider"]:
                                accumulated_data["Provider"][provider_name][resource_key] = provider_data
                            else:
                                accumulated_data["Provider"][provider_name][resource_key].update(provider_data)
                            # Increment the counter for the next occurrence of the same provider
                            provider_counter[provider_name] += 1
            except json.JSONDecodeError as e:
                print(f"Invalid JSON at {json_file_path}: {e}")

    return accumulated_data


def render_provider(provider_name, provider_data, provider_id):
    # Create an accordion for each provider
    html_content = f'<div class="accordion-item">'
    html_content += f'<h2 class="accordion-header" id="heading-{provider_id}">'
    html_content += f'<button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-{provider_id}" aria-expanded="true" aria-controls="collapse-{provider_id}">'
    html_content += f'{provider_name}'
    html_content += '</button></h2>'

    html_content += f'<div id="collapse-{provider_id}" class="accordion-collapse collapse show" aria-labelledby="heading-{provider_id}" data-bs-parent="#heading-{provider_id}">'
    html_content += '<div class="accordion-body">'

    # Render the first level Bibliographic Info and List of Volumes
    if "Bibliographic Info" in provider_data and "List of Volumes" in provider_data:
        html_content += render_bibliographic_info(provider_data, f'{provider_id}')
        html_content += render_list_of_volumes(provider_data, f'{provider_id}')

    # Handle additional resource layers like resource-1, resource-2
    for key in provider_data:
        if key.startswith("Resource-"):
            html_content += f'<div class="accordion-item">'
            html_content += f'<h2 class="accordion-header" id="heading-{key}-{provider_id}">'
            html_content += f'<button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-{key}-{provider_id}" aria-expanded="false" aria-controls="collapse-{key}-{provider_id}">'
            html_content += f'{key}'
            html_content += '</button></h2>'
            html_content += f'<div id="collapse-{key}-{provider_id}" class="accordion-collapse collapse" aria-labelledby="heading-{key}-{provider_id}" data-bs-parent="#heading-{key}-{provider_id}">'
            html_content += '<div class="accordion-body">'
            html_content += render_bibliographic_info(provider_data[key], f'{key}-{provider_id}')
            html_content += render_list_of_volumes(provider_data[key], f'{key}-{provider_id}')
            html_content += '</div></div></div>'

    html_content += '</div></div></div>'
    return html_content


def render_bibliographic_info(provider_data, parent_id):
    if "Bibliographic Info" in provider_data:
        html_content = '<div class="accordion-item">'
        html_content += '<h2 class="accordion-header">'
        html_content += f'<button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-bibliographic-{parent_id}" aria-expanded="false" aria-controls="collapse-bibliographic">'
        html_content += 'Bibliographic Information'
        html_content += '</button></h2>'
        html_content += f'<div id="collapse-bibliographic-{parent_id}" class="accordion-collapse collapse">'
        html_content += '<div class="accordion-body"><ul>'
        for key, value in provider_data["Bibliographic Info"].items():
            html_content += f'<li><strong>{key}:</strong> {value}</li>'
        html_content += '</ul></div></div></div>'
        return html_content
    return ''


def render_list_of_volumes(provider_data, parent_id):
    if "List of Volumes" in provider_data:
        html_content = '<div class="accordion-item">'
        html_content += '<h2 class="accordion-header">'
        for title in provider_data["List of Volumes"].keys():
            html_content += f'<button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-volumes-{parent_id}" aria-expanded="false" aria-controls="collapse-volumes">'
            html_content += f'List of Volumes - {title}'
            html_content += '</button></h2>'
            html_content += f'<div id="collapse-volumes-{parent_id}" class="accordion-collapse collapse">'
            html_content += '<div class="accordion-body"><ul>'
            for volume in provider_data["List of Volumes"][title]:
                html_content += f'<li><strong>{volume["Volume"]} ({volume["Year"]}):</strong> <a href="{volume["URL"]}">View Source</a> | <a href="https://ocr.berd-nfdi.de/viewer?tx_dlf%5Bid%5D={volume["METS"]}">Open with OCR-Viewer</a> | <a href="{volume["METS"]}">View METS</a></li>'
            html_content += '</ul></div></div></div>'
        return html_content
    return ''


def process_and_render_html(data):
    # Start HTML with Bootstrap CSS and JS includes
    html_content = '''<html>
<head>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</head>
<body>
    <div class="accordion" id="accordionProviders">'''

    provider_id_counter = 0  # To ensure unique IDs for each provider and inner accordion

    for provider_name, provider_data in data["Provider"].items():
        provider_id = f'provider-{provider_id_counter}'
        html_content += render_provider(provider_name, provider_data, provider_id)
        provider_id_counter += 1

    # Close HTML tags
    html_content += '''
    </div>
</body>
</html>'''

    return html_content


def save_html(output_file, html_content):
    # Pretty-print the HTML using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    pretty_html = soup.prettify()

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(pretty_html)

def get_deepest_subfolders(main_folder):
    deepest_subfolders = []
    for dirpath, dirnames, filenames in os.walk(main_folder):
        # If the directory has no subdirectories, it's considered a deepest subfolder
        if not dirnames:
            deepest_subfolders.append(dirpath)
    return deepest_subfolders

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: render_json_to_html.py <main_folder>")
        sys.exit(1)

    main_folder = sys.argv[1]

    # Find the deepest subfolders
    deepest_subfolders = get_deepest_subfolders(main_folder)

    for subfolder_path in deepest_subfolders:
        # Load and accumulate JSON data for the current deepest subfolder
        accumulated_data = load_and_accumulate_json_files(subfolder_path)

        if accumulated_data["Provider"]:  # Only create a file if data is found
            # Generate and render the HTML content
            html_content = process_and_render_html(accumulated_data)

            # Save the rendered HTML to a file in the current subfolder
            output_file = os.path.join(subfolder_path, 'data.html')
            save_html(output_file, html_content)
            print(f"HTML file generated in: {output_file}")