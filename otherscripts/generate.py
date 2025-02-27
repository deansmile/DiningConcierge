import json
from collections import defaultdict

# Input and Output Files
INPUT_FILE_PATH = 'result.json'   # Path to the original JSON file
OUTPUT_FILE_PATH = 'filtered_data.json'  # Output file for filtered data

# Cuisines to Filter and Limit
TARGET_CUISINES = ['italian', 'mexican', 'chinese']  # Customize the cuisines you want
MAX_COUNT_PER_CUISINE = 50

def generate_filtered_json(input_file, output_file):
    """ Read JSON file, filter and limit data, and generate new JSON for upload """
    print("Reading JSON data...")

    # Counter to track the number of documents per cuisine
    cuisine_counter = defaultdict(int)
    total_written = 0

    with open(input_file, 'r') as f:
        lines = f.readlines()

    # Collect the filtered documents
    filtered_lines = []

    # Iterate through lines, skipping index metadata lines
    for i in range(0, len(lines), 2):
        metadata = json.loads(lines[i])   # Index metadata
        document = json.loads(lines[i+1]) # Actual document data
        doc_id = metadata['index']['_id']
        cuisine = document.get('cuisine', '').lower()

        # Check if the cuisine is one of the target cuisines and limit to MAX_COUNT_PER_CUISINE
        if cuisine in TARGET_CUISINES and cuisine_counter[cuisine] < MAX_COUNT_PER_CUISINE:
            # Add the metadata and document lines to the output
            filtered_lines.append(lines[i].strip())    # Metadata
            filtered_lines.append(lines[i+1].strip()) # Document data
            cuisine_counter[cuisine] += 1
            total_written += 1

        # Stop once the total count reaches the limit
        if total_written >= MAX_COUNT_PER_CUISINE * len(TARGET_CUISINES):
            break

    # Write the filtered data to a new JSON file
    with open(output_file, 'w') as f_out:
        for line in filtered_lines:
            f_out.write(line + '\n')

    print("\n✅ Filtered data has been written to:", output_file)
    print("✅ Total documents:", total_written)
    print("✅ Uploaded count per cuisine:", dict(cuisine_counter))

if __name__ == "__main__":
    generate_filtered_json(INPUT_FILE_PATH, OUTPUT_FILE_PATH)
