import json
import pathlib


def main():
    tasks = json.loads(pathlib.Path("tools/agent_orchestrator_tasks.json").read_text())
    high = [t for t in tasks if t["priority"] == "high"]
    out = pathlib.Path("c:/tmp/dispatch_batch_1.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        f.write(f"# First 3 HIGH priority tasks (of {len(high)})\n\n")
        for task in high[:3]:
            f.write(f"## {task['title']}\n")
            f.write(f"- Model: `{task['target_model']}`\n")
            f.write(f"- File: `{task['file_path']}:{task['line_start']}`\n")
            f.write(f"- Category: {task['category']}\n")
            f.write("```\n" + task["prompt"] + "\n```\n\n")
    print(out)


if __name__ == "__main__":
    main()
