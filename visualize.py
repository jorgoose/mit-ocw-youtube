import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Read the CSV
df = pd.read_csv('mit_courses_2024-12-26_213033.csv')

# Create figure with subplots
fig = make_subplots(rows=3, cols=1, 
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
                  showlegend=True),
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
              showlegend=True),
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
              showlegend=True),
    row=3, col=1
)

# Update layout
fig.update_layout(
    title_text="MIT OCW Course Video Views Analysis",
    height=1200,
    showlegend=True,
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=1.0
    )
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