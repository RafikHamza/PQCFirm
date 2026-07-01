import argparse
import json
import os
import sys
from .scanner import Scanner

def format_table(findings: list) -> str:
    if not findings:
        return "No findings found."
        
    # Column widths
    headers = ["File", "Line", "Rule", "Severity", "Message"]
    rows = []
    for f in findings:
        rows.append([
            os.path.basename(f.file_path),
            str(f.line),
            f.rule_id,
            f.severity.upper(),
            f.message
        ])
        
    widths = [max(len(row[i]) for row in [headers] + rows) for i in range(len(headers))]
    
    # Format line
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    
    lines = [sep]
    header_str = "|" + "|".join(f" {headers[i].ljust(widths[i])} " for i in range(len(headers))) + "|"
    lines.append(header_str)
    lines.append(sep)
    
    for row in rows:
        row_str = "|" + "|".join(f" {row[i].ljust(widths[i])} " for i in range(len(widths))) + "|"
        lines.append(row_str)
        
    lines.append(sep)
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="PQCFirm Static Analyzer for post-quantum crypto migration")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dir", help="Directory to scan")
    group.add_argument("--file", help="File to scan")
    
    parser.add_argument("--format", choices=["json", "table", "text"], default="table", help="Output format")
    parser.add_argument("--rules", help="Comma-separated list of rules to enable (e.g. R01,R03,R04)")
    
    args = parser.parse_args()
    
    enabled_rules = None
    if args.rules:
        enabled_rules = [r.strip() for r in args.rules.split(",")]
        
    scanner = Scanner(rules=enabled_rules)
    
    if args.file:
        findings = scanner.scan_file(args.file)
    else:
        findings = scanner.scan_directory(args.dir)
        
    if args.format == "json":
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    elif args.format == "text":
        for f in findings:
            print(f"[{f.rule_id}] {f.severity.upper()} - {f.file_path}:{f.line}:{f.col} - {f.message} (Suggestion: {f.suggestion})")
    else:
        print(format_table(findings))
        
    sys.exit(0 if not findings else 1)

if __name__ == "__main__":
    main()
