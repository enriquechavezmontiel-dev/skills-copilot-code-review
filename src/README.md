# Mergington High School Activities and Announcements API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities, while signed-in teachers can manage school announcements.

## Features

- View all available extracurricular activities
- Sign up for activities
- View active school announcements on the public banner
- Manage announcements when signed in as a teacher

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |
| GET    | `/announcements`                                                  | Get all announcements, including their active status               |
| GET    | `/announcements/active`                                           | Get only active announcements for the public banner                |
| POST   | `/announcements?teacher_username=teacher`                         | Create a new announcement                                          |
| PUT    | `/announcements/{announcement_id}?teacher_username=teacher`       | Update an existing announcement                                    |
| DELETE | `/announcements/{announcement_id}?teacher_username=teacher`       | Delete an existing announcement                                    |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

3. **Announcements** - Stored in MongoDB and rendered dynamically in the frontend:
   - Title
   - Message
   - Optional start date
   - Required expiration date
   - Creator metadata and active/expired status

Example data for activities, teachers, and announcements is seeded into MongoDB when the corresponding collection is empty.
