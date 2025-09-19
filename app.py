import os
from flask import Flask, request, render_template, redirect, url_for, send_file, flash
import pandas as pd
import plotly.express as px
from werkzeug.utils import secure_filename
from io import BytesIO

# Setup
BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DATA_FOLDER = os.path.join(BASE_DIR, 'data')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'csv'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'dev-secret-key'  # change in production


# Helpers
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_numeric_columns(df):
    return df.select_dtypes(include=['number']).columns.tolist()


# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'dataset' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['dataset']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            return redirect(url_for('dashboard', filename=filename))

        flash('Only CSV files are allowed')
        return redirect(request.url)

    # list sample datasets
    sample_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
    return render_template('index.html', samples=sample_files)


@app.route('/dashboard')
def dashboard():
    filename = request.args.get('filename')
    sample = request.args.get('sample')

    filepath = None
    if filename:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    elif sample:
        filepath = os.path.join(DATA_FOLDER, sample)

    if not filepath or not os.path.exists(filepath):
        flash('Dataset not found. Please upload or choose a sample.')
        return redirect(url_for('index'))

    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        flash(f'Error reading CSV: {e}')
        return redirect(url_for('index'))

    # preview
    preview_html = df.head(10).to_html(classes='table table-bordered table-striped', index=False)

    # chart controls
    x_col = request.args.get('x_col')
    y_col = request.args.get('y_col')
    chart_type = request.args.get('chart_type', 'line')

    all_columns = df.columns.tolist()
    numeric_cols = get_numeric_columns(df)

    chart_div = ''
    if x_col and y_col and x_col in all_columns and y_col in all_columns:
        try:
            if chart_type == 'line':
                fig = px.line(df, x=x_col, y=y_col, title=f'{y_col} vs {x_col}')
            elif chart_type == 'bar':
                fig = px.bar(df, x=x_col, y=y_col, title=f'{y_col} vs {x_col}')
            elif chart_type == 'scatter':
                fig = px.scatter(df, x=x_col, y=y_col, title=f'{y_col} vs {x_col}')
            chart_div = fig.to_html(full_html=False, include_plotlyjs='cdn')
        except Exception as e:
            flash(f'Chart error: {e}')

    return render_template('dashboard.html',
                           preview_html=preview_html,
                           filename=filename,
                           sample=sample,
                           columns=all_columns,
                           numeric_columns=numeric_cols,
                           chart_div=chart_div,
                           selected_x=x_col,
                           selected_y=y_col,
                           chart_type=chart_type)


@app.route('/download')
def download():
    filename = request.args.get('filename')
    sample = request.args.get('sample')

    filepath = None
    if filename:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    elif sample:
        filepath = os.path.join(DATA_FOLDER, sample)

    if not filepath or not os.path.exists(filepath):
        flash('Dataset not found.')
        return redirect(url_for('index'))

    df = pd.read_csv(filepath)

    buf = BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name='dataset.csv',
                     mimetype='text/csv')


if __name__ == '__main__':
    app.run(debug=True)
