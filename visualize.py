import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Add after imports
plotly_template = "plotly_dark"

# Read the CSV
df = pd.read_csv('mit_courses_2024-12-26_213033.csv')

# Create figure with subplots
fig = make_subplots(
    rows=3, cols=1, 
    subplot_titles=('Raw View Counts by Course',
                   'View Counts as Percentage of First Video',
                   'Maximum Possible Retention Since First Video'),
    vertical_spacing=0.1,
    row_heights=[1200, 1200, 1200])

# Group by CourseTitle
for course in df['CourseTitle'].unique():
    course_data = df[df['CourseTitle'] == course].sort_values('Position')
    
    # Graph 1: Raw view counts
    fig.add_trace(
        go.Scatter(x=course_data['Position'], 
                  y=course_data['ViewCount'],
                  name=course,
                  mode='lines+markers',
                  showlegend=False),
        row=1, col=1
    )
    
    # Graph 2: Percentage of first video
    first_views = course_data.iloc[0]['ViewCount']
    percentages = course_data['ViewCount'] / first_views * 100
    fig.add_trace(
        go.Scatter(x=course_data['Position'],
                  y=percentages,
                  name=course,
                  mode='lines+markers',
                  showlegend=False),
        row=2, col=1
    )
    
    # Graph 3: Maximum possible retention
    first_views = course_data.iloc[0]['ViewCount']
    retention = [100]  # First video is always 100%
    
    for _, row in course_data.iloc[1:].iterrows():
        raw_retention = (row['ViewCount'] / first_views) * 100  # Always compare to first video
        capped_retention = min(raw_retention, retention[-1])
        retention.append(capped_retention)
    
    fig.add_trace(
        go.Scatter(x=course_data['Position'],
                  y=retention,
                  name=course,
                  mode='lines+markers',
                  showlegend=False),
        row=3, col=1
    )

# Add median line to Graph 2
positions = df['Position'].unique()
medians = []
for pos in positions:
    pos_data = df[df['Position'] == pos]
    if len(pos_data) > 0:
        first_views = df.groupby('CourseTitle').first()['ViewCount']
        percentages = pos_data['ViewCount'] / first_views[pos_data['CourseTitle']].values * 100
        medians.append(np.median(percentages))
    
fig.add_trace(
    go.Scatter(x=positions,
              y=medians,
              name='Median',
              mode='lines',
              line=dict(color='black', width=2),
              showlegend=False),
    row=2, col=1
)

# Update the median calculation for Graph 3
retention_medians = []
for pos in positions:
    pos_data = df[df['Position'] == pos]
    if len(pos_data) > 0:
        if pos == min(positions):
            retention_medians.append(100)
        else:
            course_retentions = []
            for course in df['CourseTitle'].unique():
                course_data = df[df['CourseTitle'] == course].sort_values('Position')
                if len(course_data[course_data['Position'] == pos]) > 0:
                    first_views = course_data.iloc[0]['ViewCount']
                    curr_views = course_data[course_data['Position'] == pos].iloc[0]['ViewCount']
                    raw_retention = (curr_views / first_views) * 100
                    capped_retention = min(raw_retention, retention_medians[-1])
                    course_retentions.append(capped_retention)
            retention_medians.append(np.median(course_retentions) if course_retentions else np.nan)

fig.add_trace(
    go.Scatter(x=positions,
              y=retention_medians,
              name='Median Retention',
              mode='lines',
              line=dict(color='black', width=2),
              showlegend=False),
    row=3, col=1
)

# Update layout to use dark theme
fig.update_layout(
    template=plotly_template,
    paper_bgcolor='#1e1e1e',
    plot_bgcolor='#1e1e1e',
    height=1200,
    showlegend=False,
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="right",
        x=0
    ),
    font=dict(color='#ffffff')
)

fig.update_xaxes(title_text="Video Position in Course", row=3, col=1)
fig.update_yaxes(title_text="Views", row=1, col=1)
fig.update_yaxes(title_text="Percentage of First Video Views", row=2, col=1)
fig.update_yaxes(title_text="Retention Percentage", row=3, col=1)

# Save the plot
fig.write_html("mit_course_views_analysis.html")

# Debug output for one course
example_course = df['CourseTitle'].unique()[0]
course_data = df[df['CourseTitle'] == example_course].sort_values('Position')

print(f"\nExample retention calculation for course: {example_course}")
print("\nPosition | Views | Retention vs First | Capped Retention")
print("-" * 60)

# Initialize tracking variables
first_views = course_data.iloc[0]['ViewCount']
retention_values = [100]  # First video is always 100%

print(f"1 | {first_views:,} | 100% | 100%")  # First video

for _, row in course_data.iloc[1:].iterrows():
    current_views = row['ViewCount']
    raw_retention = (current_views / first_views) * 100  # Compare to first video
    capped_retention = min(raw_retention, retention_values[-1])
    retention_values.append(capped_retention)
    
    print(f"{row['Position']} | {current_views:,} | {raw_retention:.1f}% | {capped_retention:.1f}%")

# Calculate average final retention across courses
final_retentions = []
for course in df['CourseTitle'].unique():
    course_data = df[df['CourseTitle'] == course].sort_values('Position')
    
    # Calculate retention for this course
    first_views = course_data.iloc[0]['ViewCount']
    retention = [100]
    for _, row in course_data.iloc[1:].iterrows():
        raw_retention = (row['ViewCount'] / first_views) * 100
        capped_retention = min(raw_retention, retention[-1])
        retention.append(capped_retention)
    
    final_retentions.append(retention[-1])

avg_final_retention = np.mean(final_retentions)

print("\n" + "="*60)
print(f"Average Final Retention Across All Courses: {avg_final_retention:.1f}%")
print("="*60)

def calculate_stats(df):
    # Calculate final retentions
    final_retentions = []
    for course in df['CourseTitle'].unique():
        course_data = df[df['CourseTitle'] == course].sort_values('Position')
        first_views = course_data.iloc[0]['ViewCount']
        retention = [100]
        for _, row in course_data.iloc[1:].iterrows():
            raw_retention = (row['ViewCount'] / first_views) * 100
            capped_retention = min(raw_retention, retention[-1])
            retention.append(capped_retention)
        final_retentions.append(retention[-1])
    
    return {
        'avg_final_retention': np.mean(final_retentions),
        'median_final_retention': np.median(final_retentions),
        'total_courses': len(df['CourseTitle'].unique()),
        'total_videos': len(df)
    }

def get_html_style():
    return """
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, 
                         "Helvetica Neue", Arial, sans-serif;
            background-color: #121212;
            color: #ffffff;
            margin: 0;
        }
        .container { 
            max-width: 1800px; 
            margin: 0 auto; 
            padding: 20px;
            background-color: #1e1e1e;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-box {
            background: #2d2d2d;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            border: 1px solid #3d3d3d;
        }
        .stat-value { 
            font-size: 24px; 
            font-weight: bold; 
            color: #58a6ff; 
        }
        .stat-label { 
            font-size: 14px; 
            color: #c9d1d9; 
            margin-top: 5px; 
        }
        .kaggle-wrapper {
            display: flex;
            justify-content: center;
            width: 100%;
            margin-top: 30px;
        }
        
        .kaggle-card {
            display: flex;
            align-items: center;
            background: #2d2d2d;
            border-radius: 8px;
            padding: 20px;
            max-width: 500px;
            border: 1px solid #3d3d3d;
            transition: all 0.2s ease;
            text-decoration: none;
            color: inherit;
        }
        
        .kaggle-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            border-color: #58a6ff;
        }
        
        .kaggle-logo {
            width: 24px;
            height: 24px;
            margin-right: 15px;
        }
        
        .kaggle-text {
            font-size: 16px;
            color: #c9d1d9;
        }
        .page-title {
            font-size: 32px;
            font-weight: bold;
            color: #ffffff;
            text-align: center;
            margin: 20px 0 40px 0;
        }
        .title-container {
            text-align: center;
            margin: 20px 0 40px 0;
        }
        .main-title {
            font-size: 32px;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 8px;
        }
        .subtitle {
            font-size: 18px;
            color: #8b949e;
            font-weight: normal;
        }
    </style>
    """

def get_stats_html(stats):
    return f"""
    <div class="stats-grid">
        <div class="stat-box">
            <div class="stat-value">{stats['avg_final_retention']:.1f}%</div>
            <div class="stat-label">Average Final Retention</div>
        </div>
        <div class="stat-box">
            <div class="stat-value">{stats['median_final_retention']:.1f}%</div>
            <div class="stat-label">Median Final Retention</div>
        </div>
        <div class="stat-box">
            <div class="stat-value">{stats['total_courses']}</div>
            <div class="stat-label">Total Courses</div>
        </div>
        <div class="stat-box">
            <div class="stat-value">{stats['total_videos']}</div>
            <div class="stat-label">Total Videos</div>
        </div>
    </div>
    """

def get_kaggle_card():
    kaggle_svg = '''<svg class="kaggle-logo" viewBox="0 0 24 24" fill="#20BEFF"><path d="M18.825 23.859c-.022.092-.117.141-.281.141h-3.139c-.187 0-.351-.082-.492-.248l-5.178-6.589-1.448 1.374v5.111c0 .235-.117.352-.351.352H5.505c-.236 0-.354-.117-.354-.352V.353c0-.233.118-.353.354-.353h2.431c.234 0 .351.12.351.353v14.343l6.203-6.272c.165-.165.33-.246.495-.246h3.239c.144 0 .236.06.285.18.046.149.034.255-.036.315l-6.555 6.344 6.836 8.507c.095.104.117.208.07.358"/></svg>'''
    
    return f"""
    <div class="kaggle-wrapper">
        <a href="https://www.kaggle.com/datasets/jorgoose/mit-opencourseware-youtube-course-data" 
           class="kaggle-card" target="_blank" rel="noopener">
            {kaggle_svg}
            <span class="kaggle-text">View Dataset on Kaggle</span>
        </a>
    </div>
    """
# Update save_visualization() to move title
def save_visualization(fig, stats):
    plotly_html = fig.to_html(full_html=False, include_plotlyjs=True)
    
    html_content = f"""
    <!DOCTYPE html>
    <html data-theme="dark">
    <head>
        <title>MIT OpenCourseWare YouTube Viewer Data</title>
        <meta name="color-scheme" content="dark">
        {get_html_style()}
    </head>
    <body>
        <div class="container">
            <div class="title-container">
                <h1 class="main-title">MIT OpenCourseWare YouTube Viewerership Data</h1>
                <div class="subtitle">View counts and retention across video lectures</div>
            </div>
            {get_stats_html(stats)}
            {plotly_html}
            {get_kaggle_card()}
        </div>
    </body>
    </html>
    """
    
    with open("index.html", "w", encoding='utf-8') as f:
        f.write(html_content)

# Calculate stats and save visualization
stats = calculate_stats(df)
save_visualization(fig, stats)