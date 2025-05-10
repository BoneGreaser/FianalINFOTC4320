from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reservations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Admin(db.Model):
    __tablename__ = 'admins'
    username = db.Column(db.String(80), primary_key=True)
    password = db.Column(db.String(200), nullable=False)

class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    passengerName = db.Column(db.String(100), nullable=False)
    seatRow = db.Column(db.Integer, nullable=False)
    seatColumn = db.Column(db.Integer, nullable=False)
    eTicketNumber = db.Column(db.String(100), nullable=False)
    created = db.Column(db.DateTime, default=db.func.current_timestamp())

    def format_reservation(self):
        return f"{self.passengerName}:\tRow {self.seatRow + 1}\tSeat {self.seatColumn + 1}\tTicket Confirmation: {self.eTicketNumber}"


#from project page
def get_cost_matrix():
    cost_matrix = [[100, 75, 50, 100] for row in range(12)]
    return cost_matrix

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        report = request.form.get('report')
        if report == 'admin':
            return redirect(url_for('admin'))
        elif report == 'reservation':
            return redirect(url_for('reservations'))
    return render_template('index.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    error_message = None

    #tried to check if admin already logged in, Once I log in one I can always vist page again. Must go to ingonito to login again.
    if 'admin_logged_in' not in session:
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            if not username or not password:
                error_message = 'You must enter a username and password.'
            else:
                admin = Admin.query.filter_by(username=username).first()
                if admin and admin.password == password:
                    session['admin_logged_in'] = True
                    flash('Login successful!', 'success')
                    return redirect(url_for('admin'))
                else:
                    error_message = 'Invalid username or password.'

        return render_template('admin.html', error_message=error_message, logged_in=False)

    seating_chart = [['O' for _ in range(4)] for _ in range(12)]
    total_sales = 0
    reservations = Reservation.query.all()

    for reservation in reservations:
        seating_chart[reservation.seatRow][reservation.seatColumn] = 'X'
        total_sales += get_cost_matrix()[reservation.seatRow][reservation.seatColumn]

    return render_template(
        'admin.html',
        seating_chart=seating_chart,
        total_sales=total_sales,
        reservations=reservations,
        error_message=error_message,
        logged_in=True)

@app.route('/reservations', methods=['GET', 'POST'])
def reservations():
    seating_chart = [['O' for _ in range(4)] for _ in range(12)]
    reservations = Reservation.query.all()

    #seat marker
    for reservation in reservations:
        seating_chart[reservation.seatRow][reservation.seatColumn] = 'X'

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        seat_row = int(request.form.get('seat_row'))
        seat_column = int(request.form.get('seat_column'))

        if not first_name or not last_name or seat_row is None or seat_column is None:
            flash('All fields are required.', 'error')
        elif seating_chart[seat_row][seat_column] == 'X':
            flash('The selected seat is already taken. Please choose another seat.', 'error')
        else:
            #ticket num generator
            infotc = "INFOTC4320"
            e_ticket = ''.join(
                first_name[i] + infotc[i] if i < len(first_name) else infotc[i]
                for i in range(len(infotc)))

            new_reservation = Reservation(
                passengerName=f"{first_name} {last_name}",
                seatRow=seat_row,
                seatColumn=seat_column,
                eTicketNumber=e_ticket)
            db.session.add(new_reservation)
            db.session.commit()

            flash(
                f"Reservation for {first_name} complete. Row: {seat_row + 1} Seat: {seat_column + 1} is now reserved. Enjoy your trip!"
                f" Your e-ticket number is: {e_ticket}",
                'success')
            return redirect(url_for('reservations'))

    #send available rows/seats to template
    available_rows = [i for i in range(12) if 'O' in seating_chart[i]]
    available_seats = {row: [col for col, seat in enumerate(seating_chart[row]) if seat == 'O'] for row in available_rows}

    return render_template(
        'reservations.html',
        seating_chart=seating_chart,
        available_rows=available_rows,
        available_seats=available_seats)

@app.route('/delete_reservation/<int:reservation_id>', methods=['POST'])
def delete_reservation(reservation_id):
    if 'admin_logged_in' not in session:
        flash('You must be logged in as an admin to perform this action.', 'error')
        return redirect(url_for('admin'))

    reservation = Reservation.query.get(reservation_id)
    if reservation:
        db.session.delete(reservation)
        db.session.commit()
        flash('Reservation deleted successfully!', 'success')
    else:
        flash('Reservation not found.', 'error')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)