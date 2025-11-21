import json
import webbrowser
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from urllib.parse import parse_qs, urlparse
import heapq

# ==================== Data Structures ====================

class TrieNode:
    def __init__(self):
        self.children = {}
        self.contact = None

class ContactTrie:
    def __init__(self):
        self.root = TrieNode()
    
    def insert(self, name, phone, email):
        node = self.root
        for char in name.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.contact = {'name': name, 'phone': phone, 'email': email}
    
    def search(self, name):
        node = self.root
        for char in name.lower():
            if char not in node.children:
                return None
            node = node.children[char]
        return node.contact
    
    def delete(self, name):
        def _delete(node, name, index):
            if index == len(name):
                if node.contact is None:
                    return False
                node.contact = None
                return len(node.children) == 0
            
            char = name[index].lower()
            if char not in node.children:
                return False
            
            should_delete = _delete(node.children[char], name, index + 1)
            if should_delete:
                del node.children[char]
                return len(node.children) == 0 and node.contact is None
            return False
        
        _delete(self.root, name, 0)
    
    def get_all_sorted(self):
        contacts = []
        def _traverse(node):
            if node.contact:
                contacts.append(node.contact)
            for child in sorted(node.children.keys()):
                _traverse(node.children[child])
        
        _traverse(self.root)
        return contacts
    
    def search_prefix(self, prefix):
        """Search for all contacts starting with prefix"""
        node = self.root
        prefix_lower = prefix.lower()
        for char in prefix_lower:
            if char not in node.children:
                return []
            node = node.children[char]
        
        contacts = []
        def _traverse(n):
            if n.contact:
                contacts.append(n.contact)
            for child in sorted(n.children.keys()):
                _traverse(n.children[child])
        
        _traverse(node)
        return contacts

class ReminderQueue:
    def __init__(self):
        self.heap = []
    
    def add(self, text, timestamp):
        heapq.heappush(self.heap, (timestamp, text))
    
    def get_all(self):
        return sorted(self.heap, key=lambda x: x[0])
    
    def remove(self, text, timestamp):
        self.heap = [(t, txt) for t, txt in self.heap if not (t == timestamp and txt == text)]
        heapq.heapify(self.heap)

class ProjectQueue:
    def __init__(self):
        self.projects = []
    
    def add(self, name, start_date, end_date):
        heapq.heappush(self.projects, (start_date, name, end_date))
    
    def get_all(self):
        return sorted(self.projects, key=lambda x: x[0])
    
    def remove(self, name, start_date):
        self.projects = [(s, n, e) for s, n, e in self.projects if not (n == name and s == start_date)]
        heapq.heapify(self.projects)

# ==================== Manager ====================

class DataManager:
    def __init__(self):
        self.contacts = ContactTrie()
        self.reminders = ReminderQueue()
        self.projects = ProjectQueue()
    
    def get_data(self):
        return {
            'contacts': self.contacts.get_all_sorted(),
            'reminders': [{'text': t, 'time': ts} for ts, t in self.reminders.get_all()],
            'projects': [{'name': n, 'start': s, 'end': e} for s, n, e in self.projects.get_all()]
        }

# ==================== HTTP Handler ====================

manager = DataManager()

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(get_html().encode())
        elif self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(manager.get_data()).encode())
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        data = json.loads(body)
        
        action = data.get('action')
        
        if action == 'add_contact':
            manager.contacts.insert(data['name'], data['phone'], data['email'])
        elif action == 'delete_contact':
            manager.contacts.delete(data['name'])
        elif action == 'add_reminder':
            manager.reminders.add(data['text'], data['timestamp'])
        elif action == 'delete_reminder':
            manager.reminders.remove(data['text'], data['timestamp'])
        elif action == 'add_project':
            manager.projects.add(data['name'], data['start'], data['end'])
        elif action == 'delete_project':
            manager.projects.remove(data['name'], data['start'])
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(manager.get_data()).encode())
    
    def log_message(self, format, *args):
        pass

def get_html():
    return '''<!DOCTYPE html>
<html>
<head>
    <title>Contact & Task Manager</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: black; text-align: center; margin-bottom: 30px; font-size: 2.5em; }
        .search-box {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .search-box input {
            width: 100%;
            font-size: 16px;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
        }
        .search-box input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
        }
        .sections { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 25px; }
        .section {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .section h2 { color: #667eea; margin-bottom: 20px; font-size: 1.5em; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; color: #333; font-weight: 500; margin-bottom: 5px; }
        input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
        input:focus, textarea:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.3s;
            width: 100%;
        }
        button:hover { background: #5568d3; }
        .item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .item-content { flex: 1; }
        .item-name { font-weight: 600; color: #333; }
        .item-detail { font-size: 13px; color: #666; margin-top: 3px; }
        .btn-delete {
            background: #e74c3c;
            padding: 6px 12px;
            font-size: 12px;
            width: auto;
            margin-left: 10px;
        }
        .btn-delete:hover { background: #c0392b; }
        .items-list { max-height: 400px; overflow-y: auto; }
        .empty { color: #999; font-style: italic; text-align: center; padding: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Contact & Task Manager</h1>
        <div class="search-box">
            <input type="text" id="globalSearch" placeholder="Filter contacts, reminders, and projects...">
        </div>
        <div class="sections">
            <!-- Contacts Section -->
            <div class="section">
                <h2>Contacts</h2>
                <div class="form-group">
                    <label>Name</label>
                    <input type="text" id="contactName" placeholder="John Doe">
                </div>
                <div class="form-group">
                    <label>Phone</label>
                    <input type="text" id="contactPhone" placeholder="(555) 123-4567">
                </div>
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" id="contactEmail" placeholder="john@example.com">
                </div>
                <button onclick="addContact()">Add Contact</button>
                <div class="items-list" id="contactsList" style="margin-top: 20px;"></div>
            </div>
            
            <!-- Reminders Section -->
            <div class="section">
                <h2>Reminders</h2>
                <div class="form-group">
                    <label>Reminder Text</label>
                    <input type="text" id="reminderText" placeholder="Call client">
                </div>
                <div class="form-group">
                    <label>Date & Time</label>
                    <input type="datetime-local" id="reminderTime">
                </div>
                <button onclick="addReminder()">Add Reminder</button>
                <div class="items-list" id="remindersList" style="margin-top: 20px;"></div>
            </div>
            
            <!-- Projects Section -->
            <div class="section">
                <h2>Projects</h2>
                <div class="form-group">
                    <label>Project Name</label>
                    <input type="text" id="projectName" placeholder="Website Redesign">
                </div>
                <div class="form-group">
                    <label>Start Date</label>
                    <input type="date" id="projectStart">
                </div>
                <div class="form-group">
                    <label>End Date</label>
                    <input type="date" id="projectEnd">
                </div>
                <button onclick="addProject()">Add Project</button>
                <div class="items-list" id="projectsList" style="margin-top: 20px;"></div>
            </div>
        </div>
    </div>

    <script>
        let allData = {};

        function loadData() {
            fetch('/api/data')
                .then(r => r.json())
                .then(data => {
                    allData = data;
                    renderContacts(data.contacts);
                    renderReminders(data.reminders);
                    renderProjects(data.projects);
                });
        }

        function filterBySearch(searchTerm) {
            const term = searchTerm.toLowerCase();
            if (!term) {
                loadData();
                return;
            }
            
            const filteredContacts = allData.contacts.filter(c => 
                c.name.toLowerCase().includes(term) || 
                c.phone.toLowerCase().includes(term) || 
                c.email.toLowerCase().includes(term)
            );
            const filteredReminders = allData.reminders.filter(r => 
                r.text.toLowerCase().includes(term)
            );
            const filteredProjects = allData.projects.filter(p => 
                p.name.toLowerCase().includes(term)
            );
            
            renderContacts(filteredContacts);
            renderReminders(filteredReminders);
            renderProjects(filteredProjects);
        }

        function renderContacts(contacts) {
            const list = document.getElementById('contactsList');
            list.innerHTML = contacts.length ? '' : '<div class="empty">No contacts yet</div>';
            contacts.forEach(c => {
                const div = document.createElement('div');
                div.className = 'item';
                div.innerHTML = `
                    <div class="item-content">
                        <div class="item-name">${c.name}</div>
                        <div class="item-detail">${c.phone}</div>
                        <div class="item-detail">${c.email}</div>
                    </div>
                    <button class="btn-delete" onclick="deleteContact('${c.name.replace(/'/g, "\\'")}')">Delete</button>
                `;
                list.appendChild(div);
            });
        }

        function renderReminders(reminders) {
            const list = document.getElementById('remindersList');
            list.innerHTML = reminders.length ? '' : '<div class="empty">No reminders yet</div>';
            reminders.forEach(r => {
                const div = document.createElement('div');
                div.className = 'item';
                const date = new Date(r.time * 1000).toLocaleString();
                div.innerHTML = `
                    <div class="item-content">
                        <div class="item-name">${r.text}</div>
                        <div class="item-detail">${date}</div>
                    </div>
                    <button class="btn-delete" onclick="deleteReminder('${r.text.replace(/'/g, "\\'")}', ${r.time})">Delete</button>
                `;
                list.appendChild(div);
            });
        }

        function renderProjects(projects) {
            const list = document.getElementById('projectsList');
            list.innerHTML = projects.length ? '' : '<div class="empty">No projects yet</div>';
            projects.forEach(p => {
                const div = document.createElement('div');
                div.className = 'item';
                div.innerHTML = `
                    <div class="item-content">
                        <div class="item-name">${p.name}</div>
                        <div class="item-detail">${p.start} to ${p.end}</div>
                    </div>
                    <button class="btn-delete" onclick="deleteProject('${p.name.replace(/'/g, "\\'")}', '${p.start}')">Delete</button>
                `;
                list.appendChild(div);
            });
        }

        function addContact() {
            const name = document.getElementById('contactName').value;
            const phone = document.getElementById('contactPhone').value;
            const email = document.getElementById('contactEmail').value;
            if (!name || !phone || !email) { alert('Fill all fields'); return; }
            
            fetch('/api/data', {
                method: 'POST',
                body: JSON.stringify({action: 'add_contact', name, phone, email})
            }).then(() => {
                document.getElementById('contactName').value = '';
                document.getElementById('contactPhone').value = '';
                document.getElementById('contactEmail').value = '';
                document.getElementById('globalSearch').value = '';
                loadData();
            });
        }

        function deleteContact(name) {
            fetch('/api/data', {
                method: 'POST',
                body: JSON.stringify({action: 'delete_contact', name})
            }).then(() => loadData());
        }

        function addReminder() {
            const text = document.getElementById('reminderText').value;
            const time = new Date(document.getElementById('reminderTime').value).getTime() / 1000;
            if (!text || !time) { alert('Fill all fields'); return; }
            
            fetch('/api/data', {
                method: 'POST',
                body: JSON.stringify({action: 'add_reminder', text, timestamp: time})
            }).then(() => {
                document.getElementById('reminderText').value = '';
                document.getElementById('reminderTime').value = '';
                document.getElementById('globalSearch').value = '';
                loadData();
            });
        }

        function deleteReminder(text, timestamp) {
            fetch('/api/data', {
                method: 'POST',
                body: JSON.stringify({action: 'delete_reminder', text, timestamp})
            }).then(() => loadData());
        }

        function addProject() {
            const name = document.getElementById('projectName').value;
            const start = document.getElementById('projectStart').value;
            const end = document.getElementById('projectEnd').value;
            if (!name || !start || !end) { alert('Fill all fields'); return; }
            
            fetch('/api/data', {
                method: 'POST',
                body: JSON.stringify({action: 'add_project', name, start, end})
            }).then(() => {
                document.getElementById('projectName').value = '';
                document.getElementById('projectStart').value = '';
                document.getElementById('projectEnd').value = '';
                document.getElementById('globalSearch').value = '';
                loadData();
            });
        }

        function deleteProject(name, start) {
            fetch('/api/data', {
                method: 'POST',
                body: JSON.stringify({action: 'delete_project', name, start})
            }).then(() => loadData());
        }

        document.getElementById('globalSearch').addEventListener('input', (e) => {
            filterBySearch(e.target.value);
        });

        loadData();
        setInterval(loadData, 5000);
    </script>
</body>
</html>'''

def start_server():
    server = HTTPServer(('localhost', 8000), RequestHandler)
    print("Server started at http://localhost:8000")
    server.serve_forever()

if __name__ == '__main__':
    thread = Thread(target=start_server, daemon=True)
    thread.start()
    webbrowser.open('http://localhost:8000')
    thread.join()