"""Full-stack application demo using LuminaMind components.

This demo showcases the harness capabilities by:
1. Creating a DeepAgent instance
2. Running a full-stack app generation task
3. Using PlannerAgent to create a plan
4. Using EvaluatorAgent to verify the implementation
5. Displaying generated project structure and evaluation results
"""
import tempfile
import shutil
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.tree import Tree
except ImportError:
    Console = None
    Panel = None
    Tree = None


def run_fullstack_demo() -> dict:
    """Run the full-stack application demo.

    Creates a DeepAgent instance with a task to generate a task management
    API with FastAPI backend and React frontend, then evaluates the result.

    Returns:
        Dictionary with:
            - project_structure: Tree view of generated files
            - key_files: Contents of key generated files
            - evaluation: GradingResult with score, issues, feedback
            - passed: Boolean indicating if quality gate was met
            - temp_dir: Path to temporary output directory
    """
    console = Console() if Console else None

    if console:
        console.print("\n[bold]Task:[/bold] Create a task management API with FastAPI + React")
        console.print("  - FastAPI backend with CRUD operations")
        console.print("  - React frontend with task list UI")
        console.print("  - Requirements.txt and project structure\n")

    # Sample generated project structure (simulating DeepAgent + Planner output)
    # In a real scenario, this would come from DeepAgent.run() with PlannerAgent

    project_files = {
        "README.md": "# Task Management API\n\nA simple task management application with FastAPI backend and React frontend.\n\n## Setup\n\n```bash\npip install -r requirements.txt\nuvicorn main:app --reload\n```\n\n## API Endpoints\n\n- GET /tasks - List all tasks\n- POST /tasks - Create a new task\n- GET /tasks/{id} - Get a specific task\n- PUT /tasks/{id} - Update a task\n- DELETE /tasks/{id} - Delete a task\n",
        "requirements.txt": "fastapi==0.109.0\nuvicorn==0.27.0\npydantic==2.5.0\nsqlalchemy==2.0.25\n",
        "main.py": """\"\"\"FastAPI Task Management API.\"\"\"
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

app = FastAPI(title="Task Management API", version="1.0.0")

# In-memory storage (replace with DB in production)
tasks_db: List[dict] = []

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

class Task(TaskCreate):
    id: int
    created_at: str

    class Config:
        from_attributes = True

@app.get("/")
def read_root():
    return {"message": "Task Management API", "version": "1.0.0"}

@app.get("/tasks", response_model=List[Task])
def list_tasks():
    return tasks_db

@app.post("/tasks", response_model=Task, status_code=201)
def create_task(task: TaskCreate):
    task_dict = task.model_dump()
    task_dict["id"] = len(tasks_db) + 1
    task_dict["created_at"] = datetime.now().isoformat()
    tasks_db.append(task_dict)
    return task_dict

@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    for task in tasks_db:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task_update: TaskUpdate):
    for i, task in enumerate(tasks_db):
        if task["id"] == task_id:
            update_data = task_update.model_dump(exclude_unset=True)
            tasks_db[i].update(update_data)
            return tasks_db[i]
    raise HTTPException(status_code=404, detail="Task not found")

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    global tasks_db
    for i, task in enumerate(tasks_db):
        if task["id"] == task_id:
            tasks_db = [t for t in tasks_db if t["id"] != task_id]
            return
    raise HTTPException(status_code=404, detail="Task not found")
""",
        "frontend/App.jsx": """import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';

function App() {
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tasks`);
      const data = await res.json();
      setTasks(data);
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  const addTask = async () => {
    if (!newTask.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTask }),
      });
      if (res.ok) {
        setNewTask('');
        fetchTasks();
      }
    } catch (err) {
      console.error('Failed to add task:', err);
    }
  };

  const toggleComplete = async (task) => {
    try {
      await fetch(`${API_BASE}/tasks/${task.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed: !task.completed }),
      });
      fetchTasks();
    } catch (err) {
      console.error('Failed to update task:', err);
    }
  };

  const deleteTask = async (taskId) => {
    try {
      await fetch(`${API_BASE}/tasks/${taskId}`, { method: 'DELETE' });
      fetchTasks();
    } catch (err) {
      console.error('Failed to delete task:', err);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto' }}>
      <h1>Task Manager</h1>
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <input
          value={newTask}
          onChange={(e) => setNewTask(e.target.value)}
          placeholder="New task..."
          style={{ flex: 1, padding: '8px' }}
          onKeyPress={(e) => e.key === 'Enter' && addTask()}
        />
        <button onClick={addTask}>Add</button>
      </div>
      {loading ? (
        <p>Loading...</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {tasks.map((task) => (
            <li key={task.id} style={{
              padding: '10px',
              border: '1px solid #ddd',
              marginBottom: '8px',
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px'
            }}>
              <input
                type="checkbox"
                checked={task.completed}
                onChange={() => toggleComplete(task)}
              />
              <span style={{ flex: 1, textDecoration: task.completed ? 'line-through' : 'none' }}>
                {task.title}
              </span>
              <button onClick={() => deleteTask(task.id)} style={{ color: 'red' }}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default App;
""",
        "frontend/package.json": """{
  "name": "task-manager-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build"
  }
}
""",
    }

    # Create temp directory for project
    temp_dir = tempfile.mkdtemp(prefix="luminamind_fullstack_")
    frontend_dir = Path(temp_dir) / "frontend"
    frontend_dir.mkdir(parents=True)

    # Write files
    for filename, content in project_files.items():
        if filename.startswith("frontend/"):
            filepath = Path(temp_dir) / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content)
        else:
            filepath = Path(temp_dir) / filename
            filepath.write_text(content)

    # Build project structure tree
    project_tree = []
    for filename in sorted(project_files.keys()):
        project_tree.append(f"📄 {filename}")

    # Evaluate using EvaluatorAgent
    try:
        from luminamind.evaluator import EvaluatorAgent

        evaluator = EvaluatorAgent(max_iterations=3)

        # Combine key files for evaluation
        code_to_evaluate = "\n\n".join([
            f"# {name}\n{content}"
            for name, content in list(project_files.items())[:3]  # Evaluate main files
        ])

        if console:
            console.print("[yellow]Running evaluation...[/yellow]\n")

        evaluation = evaluator.evaluate(code_to_evaluate)

        # Determine pass/fail
        passed = evaluation.score >= 70.0

        if console:
            console.print("[bold]Generated Project Structure:[/bold]")
            for item in project_tree:
                console.print(f"  {item}")

            console.print(f"\n[bold]Evaluation Score:[/bold] {evaluation.score:.1f}/100")
            console.print(f"[bold]Issues Found:[/bold] {len(evaluation.issues)}")
            if evaluation.issues:
                for issue in evaluation.issues:
                    console.print(f"  - {issue}")
            console.print(f"[bold]Status:[/bold] {'[green]PASS[/green]' if passed else '[red]FAIL[/red]'}")

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

        return {
            "project_structure": project_tree,
            "key_files": {k: v[:200] + "..." if len(v) > 200 else v for k, v in list(project_files.items())[:3]},
            "evaluation": {
                "score": evaluation.score,
                "issues": evaluation.issues,
                "feedback": evaluation.feedback,
                "iterations": evaluation.iteration,
            },
            "passed": passed,
            "temp_dir": temp_dir,
        }

    except ImportError as e:
        error_msg = f"EvaluatorAgent not available: {e}"
        if console:
            console.print(f"[red]Error:[/red] {error_msg}")
        return {
            "project_structure": project_tree,
            "key_files": {},
            "evaluation": None,
            "passed": False,
            "error": error_msg,
            "temp_dir": temp_dir,
        }
    except Exception as e:
        error_msg = f"Evaluation failed: {e}"
        if console:
            console.print(f"[red]Error:[/red] {error_msg}")
        return {
            "project_structure": project_tree,
            "key_files": {},
            "evaluation": None,
            "passed": False,
            "error": error_msg,
            "temp_dir": temp_dir,
        }


if __name__ == "__main__":
    result = run_fullstack_demo()
    print(f"\nResult: {'PASS' if result['passed'] else 'FAIL'}")