import os
import pandas as pd

source_folder = "././source"
target_folder = "././target"
pip_prefixes = ["PipNo_1_", "PipNo_2_", "PipNo_3_", "PipNo_4_"]
output_file = "pyclone_res.csv"

pairs = []

for source_file in os.listdir(source_folder):
    if source_file.endswith(".py"):
        source_filename = source_file
        source_file_base = os.path.splitext(source_file)[0]
        source_path = os.path.join(source_folder, source_filename)

        if not os.path.exists(source_path):
            continue

        target_fold = os.path.join(target_folder, source_file_base)
        if not os.path.exists(target_fold):
            continue

        for pip_prefix in pip_prefixes:
            refactored_file = f"{pip_prefix}{source_filename}"
            refactored_path = os.path.join(target_fold, refactored_file)

            if os.path.exists(refactored_path):
                pairs.append({
                    "code1": source_path,
                    "code2": refactored_path
                })
            else:
                print(f"Refactored file missing: {refactored_path}")

df = pd.DataFrame(pairs)
df.to_csv(output_file, index=False)
print(f"CSV saved to {output_file} with {len(df)} valid pairs.")
