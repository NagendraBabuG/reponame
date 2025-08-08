import os
from codebleu import calc_codebleu

def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def compare_code_files(source_dir, target_dir, lang="python", weights=(0.25, 0.25, 0.25, 0.25)):
    results = {}
    
    if not os.path.exists(source_dir) or not os.path.exists(target_dir):
        print(f"Source directory: {source_dir}")
        print(f"Target directory: {target_dir}")
        print("Source or target directory does not exist.")
        return results
    
    source_files = [f for f in os.listdir(source_dir) if f.endswith('.py')]
    
    for source_file in source_files:
        source_path = os.path.join(source_dir, source_file)
        file_name = os.path.splitext(source_file)[0]
        target_subdir = os.path.join(target_dir, file_name)
        
        if not os.path.exists(target_subdir):
            print(f"Target subfolder {target_subdir} does not exist. Skipping {source_file}.")
            continue
        
        source_code = read_file(source_path)
        if not source_code or not source_code.strip():
            print(f"Skipping {source_file} due to read error or empty content.")
            continue
        
        results[source_file] = {}
        
        refactored_prefixes = [f"PipNo_{i}_" for i in range(1, 5)]
        
        for prefix in refactored_prefixes:
            target_file = f"{prefix}{source_file}"
            target_path = os.path.join(target_subdir, target_file)
            
            if not os.path.exists(target_path):
                print(f"Target file {target_path} does not exist. Skipping.")
                continue
            
            target_code = read_file(target_path)
            if not target_code or not target_code.strip():
                print(f"Skipping {target_file} due to read error or empty content.")
                continue

            try:
                result = calc_codebleu(
                    references=[source_code],
                    predictions=[target_code],
                    lang=lang,
                    weights=weights,
                    tokenizer=None
                )
                results[source_file][target_file] = result
            except Exception as e:
                print(f"Error processing {source_file} vs {target_file}: {e}")
    
    return results

def write_to_txt(results, filename="codebleu_results.txt"):
    with open(filename, 'w', encoding='utf-8') as f:
        if results:
            for source_file, target_results in results.items():
                for target_file, metrics in target_results.items():
                    f.write(f"Result -  {source_file} : {target_file}\n")
                    f.write(f"CodeBLEU Score: {metrics['codebleu']:.4f}\n")
                    f.write(f"N-gram Match: {metrics['ngram_match_score']:.4f}\n")
                    f.write(f"Weighted N-gram Match: {metrics['weighted_ngram_match_score']:.4f}\n")
                    f.write(f"Syntax Match (AST): {metrics['syntax_match_score']:.4f}\n")
                    f.write(f"Dataflow Match: {metrics['dataflow_match_score']:.4f}\n\n")
        else:
            f.write("No code pairs.\n")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    source_dir = os.path.join(script_dir, "source")
    target_dir = os.path.join(script_dir, "target")
    
    results = compare_code_files(source_dir, target_dir)
    
    write_to_txt(results, "codebleu_results.txt")

if __name__ == "__main__":
    main()