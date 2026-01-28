from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'attendance.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    attendance = db.relationship('Attendance', backref='student', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'roll_no': self.roll_no,
            'name': self.name,
            'email': self.email,
            'phone': self.phone
        }

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), default='present')  # present, absent, leave
    remarks = db.Column(db.String(200))
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': self.student.name,
            'date': str(self.date),
            'status': self.status,
            'remarks': self.remarks
        }

# Routes
@app.route("/")
def index():
    return render_template('index.html')

@app.route("/students")
def students():
    all_students = Student.query.all()
    return render_template('students.html', students=all_students)

@app.route("/api/students", methods=['GET', 'POST'])
def api_students():
    if request.method == 'POST':
        data = request.get_json()
        
        # Check if student already exists
        existing = Student.query.filter_by(roll_no=data['roll_no']).first()
        if existing:
            return jsonify({'error': 'Roll number already exists'}), 400
        
        student = Student(
            roll_no=data['roll_no'],
            name=data['name'],
            email=data.get('email'),
            phone=data.get('phone')
        )
        db.session.add(student)
        db.session.commit()
        return jsonify(student.to_dict()), 201
    
    students = Student.query.all()
    return jsonify([s.to_dict() for s in students])

@app.route("/api/students/<int:id>", methods=['DELETE'])
def delete_student(id):
    student = Student.query.get_or_404(id)
    db.session.delete(student)
    db.session.commit()
    return jsonify({'message': 'Student deleted'}), 200

@app.route("/attendance")
def attendance():
    students = Student.query.all()
    today = datetime.now().date()
    return render_template('attendance.html', students=students, today=today)

@app.route("/api/attendance", methods=['POST'])
def mark_attendance():
    data = request.get_json()
    
    # Delete existing attendance for this date
    Attendance.query.filter_by(
        student_id=data['student_id'],
        date=datetime.strptime(data['date'], '%Y-%m-%d').date()
    ).delete()
    
    attendance = Attendance(
        student_id=data['student_id'],
        date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
        status=data['status'],
        remarks=data.get('remarks')
    )
    db.session.add(attendance)
    db.session.commit()
    return jsonify(attendance.to_dict()), 201

@app.route("/api/attendance/<date>")
def get_attendance(date):
    attendance_records = Attendance.query.filter_by(
        date=datetime.strptime(date, '%Y-%m-%d').date()
    ).all()
    return jsonify([a.to_dict() for a in attendance_records])

@app.route("/reports")
def reports():
    students = Student.query.all()
    return render_template('reports.html', students=students)

@app.route("/api/student-attendance/<int:student_id>")
def student_attendance(student_id):
    student = Student.query.get_or_404(student_id)
    attendance = Attendance.query.filter_by(student_id=student_id).all()
    
    total = len(attendance)
    present = len([a for a in attendance if a.status == 'present'])
    absent = len([a for a in attendance if a.status == 'absent'])
    leave = len([a for a in attendance if a.status == 'leave'])
    percentage = (present / total * 100) if total > 0 else 0
    
    return jsonify({
        'student': student.to_dict(),
        'total': total,
        'present': present,
        'absent': absent,
        'leave': leave,
        'percentage': round(percentage, 2),
        'records': [a.to_dict() for a in attendance]
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)