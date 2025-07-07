import argparse
from spinscribe.tasks.process import run_content_task

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Spinscribe content workflow")
    parser.add_argument("--title", required=True, help="Title of the content")
    parser.add_argument("--type", required=True, choices=["landing_page","article","local_article"], help="Content type")
    args = parser.parse_args()

    output = run_content_task(args.title, args.type)
    print("\n===== FINAL CONTENT OUTPUT =====\n")
    print(output)