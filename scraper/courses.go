package scraper

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/chromedp/cdproto/cdp"
	"github.com/chromedp/chromedp"
	"github.com/google/generative-ai-go/genai"
	"google.golang.org/api/option"
)

type VideoInfo struct {
	URL       string `json:"url"`
	Title     string `json:"title"`
	ViewCount int    `json:"view_count"`
	Position  int    `json:"position"` // New field
	Taxonomy  string `json:"taxonomy"`
}

type CourseInfo struct {
	URL    string      `json:"url"`
	Title  string      `json:"title"`
	Videos []VideoInfo `json:"videos"`
}

type PlaylistURL struct {
	URL string `json:"url"`
}

// GetPlaylistURLs scrapes the MIT OCW courses page and uses Gemini to extract playlist URLs
func GetPlaylistURLs() ([]PlaylistURL, error) {
	ctx, cancel := chromedp.NewContext(
		context.Background(),
		chromedp.WithLogf(log.Printf),
	)
	defer cancel()

	ctx, cancel = context.WithTimeout(ctx, 2*time.Minute)
	defer cancel()

	var urls []PlaylistURL

	err := chromedp.Run(ctx,
		chromedp.Navigate(`https://www.youtube.com/@mitocw/courses?app=desktop`),
		chromedp.Sleep(3*time.Second),
		extractPlaylistURLs(&urls),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to scrape page: %w", err)
	}

	return urls, nil
}

func cleanHTML(html string) string {
	// Cleaning rules to remove unnecessary parts of the page content, before sending to Gemini

	// Remove <head> and all contents
	html = regexp.MustCompile(`(?s)<head.*?</head>`).ReplaceAllString(html, "")

	// Remove script tags
	html = regexp.MustCompile(`(?s)<script.*?</script>`).ReplaceAllString(html, "")

	// Remove comments
	html = regexp.MustCompile(`<!--.*?-->`).ReplaceAllString(html, "")

	// Remove inline styles
	html = regexp.MustCompile(`(?s)<[^>]*style=".*?"[^>]*>`).ReplaceAllString(html, "")

	// Remove styles
	html = regexp.MustCompile(`(?s)<style.*?</style>`).ReplaceAllString(html, "")

	// Remove all SVG, canvas, and img elements
	html = regexp.MustCompile(`(?s)<svg.*?</svg>`).ReplaceAllString(html, "")
	html = regexp.MustCompile(`(?s)<canvas.*?</canvas>`).ReplaceAllString(html, "")
	html = regexp.MustCompile(`<img[^>]+>`).ReplaceAllString(html, "")

	return html
}

func GetCourseInfo() ([]CourseInfo, error) {
	urls, err := GetPlaylistURLs()
	if err != nil {
		return nil, fmt.Errorf("failed to get playlist URLs: %w", err)
	}

	apiKey := os.Getenv("GEMINI_API_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("GEMINI_API_KEY environment variable not set")
	}

	ctx, cancel := chromedp.NewContext(context.Background())
	defer cancel()

	ctx, cancel = context.WithTimeout(ctx, 30*time.Minute)
	defer cancel()

	var courses []CourseInfo
	rateLimiter := time.NewTicker(4 * time.Second)
	defer rateLimiter.Stop()

	for _, playlist := range urls {
		// Wait for rate limit
		<-rateLimiter.C

		var retries int
		const maxRetries = 3
		for {
			courseInfo, err := processCoursePlaylist(ctx, playlist, apiKey)
			if err != nil {
				if strings.Contains(err.Error(), "429") && retries < maxRetries {
					retries++
					waitTime := time.Duration(retries*4) * time.Second
					log.Printf("Rate limit hit, waiting %v seconds before retry %d/%d", waitTime.Seconds(), retries, maxRetries)
					time.Sleep(waitTime)
					continue
				}
				log.Printf("Error processing %s: %v", playlist.URL, err)
				break
			}
			courses = append(courses, courseInfo)
			log.Printf("Processed playlist: %s with %d videos", courseInfo.Title, len(courseInfo.Videos))
			break
		}
	}

	return courses, nil
}

func scrollPlaylistVideos(videos *[]VideoInfo) chromedp.ActionFunc {
	return func(ctx context.Context) error {
		seen := make(map[string]bool)
		var previousCount int

		for {
			var nodes []*cdp.Node
			if err := chromedp.Nodes(`a[href*="/watch?v="]`, &nodes).Do(ctx); err != nil {
				return err
			}

			position := len(*videos) + 1
			for _, node := range nodes {
				href := node.AttributeValue("href")
				if !seen[href] {
					seen[href] = true
					*videos = append(*videos, VideoInfo{
						URL:      href,
						Position: position,
					})
					position++
				}
			}

			if len(nodes) == previousCount {
				break
			}
			previousCount = len(nodes)

			if err := chromedp.Evaluate(`
                document.querySelector('ytd-playlist-panel-renderer').scrollTo(0, document.querySelector('ytd-playlist-panel-renderer').scrollHeight)
            `, nil).Do(ctx); err != nil {
				return err
			}
			time.Sleep(2 * time.Second)
		}
		return nil
	}
}

func extractPlaylistURLs(urls *[]PlaylistURL) chromedp.ActionFunc {
	return func(ctx context.Context) error {
		seen := make(map[string]bool)
		var totalDuplicates int

		for {
			var nodes []*cdp.Node
			if err := chromedp.Nodes(`a[href*="/playlist?list="]`, &nodes).Do(ctx); err != nil {
				return err
			}

			newUrlsFound := false
			for _, node := range nodes {
				href := node.AttributeValue("href")
				if strings.Contains(href, "/playlist?list=") {
					if !seen[href] {
						seen[href] = true
						*urls = append(*urls, PlaylistURL{URL: href})
						newUrlsFound = true
					} else {
						totalDuplicates++
					}
				}
			}

			log.Printf("Current unique URLs: %d, Duplicates found: %d", len(seen), totalDuplicates)

			if !newUrlsFound {
				break
			}

			if err := chromedp.Evaluate(`window.scrollTo(0, document.documentElement.scrollHeight)`, nil).Do(ctx); err != nil {
				return err
			}
			time.Sleep(2 * time.Second)
		}

		sortedUrls := make([]PlaylistURL, 0, len(seen))
		for url := range seen {
			sortedUrls = append(sortedUrls, PlaylistURL{URL: url})
		}
		sort.Slice(sortedUrls, func(i, j int) bool {
			return sortedUrls[i].URL < sortedUrls[j].URL
		})
		*urls = sortedUrls

		return nil
	}
}

func extractCourseMetadata(apiKey, html string) (CourseInfo, error) {
	ctx := context.Background()
	client, err := genai.NewClient(ctx, option.WithAPIKey(apiKey))
	if err != nil {
		return CourseInfo{}, fmt.Errorf("failed to create Gemini client: %w", err)
	}
	defer client.Close()

	model := client.GenerativeModel("gemini-1.5-flash")
	model.ResponseMIMEType = "application/json"
	model.ResponseSchema = &genai.Schema{
		Type: genai.TypeObject,
		Properties: map[string]*genai.Schema{
			"title": {
				Type: genai.TypeString,
			},
			"videos": {
				Type: genai.TypeArray,
				Items: &genai.Schema{
					Type: genai.TypeObject,
					Properties: map[string]*genai.Schema{
						"url": {
							Type: genai.TypeString,
						},
						"title": {
							Type: genai.TypeString,
						},
						"view_count": {
							Type: genai.TypeInteger,
						},
						"taxonomy": {
							Type: genai.TypeString,
							Enum: []string{
								"Biological Sciences",
								"Business and Management",
								"Chemistry",
								"Computer Science",
								"Design",
								"Economics",
								"Political Science",
								"Physics",
								"Mathematics",
								"Sociology",
								"Statistics",
								"Literature",
								"History",
								"Philosophy",
								"Other",
							},
						},
					},
					Required: []string{"url", "title", "view_count"},
				},
			},
		},
		Required: []string{"title", "videos"},
	}

	prompt := fmt.Sprintf(`
Extract course metadata from the following HTML:
1. Course title (from the playlist title)
2. For each video:
   - Video title
   - URL (starting with /watch?v=)
   - View count (as integer, remove "views" text)

Return as JSON:
{
  "title": "Course Title",
  "videos": [
    {
      "url": "/watch?v=xyz",
      "title": "Video Title",
      "view_count": 1234
    }
  ]
}

HTML:
%s`, html)

	resp, err := model.GenerateContent(ctx, genai.Text(prompt))
	if err != nil {
		return CourseInfo{}, fmt.Errorf("failed to generate content: %w", err)
	}

	jsonText := resp.Candidates[0].Content.Parts[0].(genai.Text)
	var courseInfo CourseInfo
	if err := json.Unmarshal([]byte(jsonText), &courseInfo); err != nil {
		return CourseInfo{}, fmt.Errorf("failed to parse JSON response: %w", err)
	}

	return courseInfo, nil
}

func processCoursePlaylist(ctx context.Context, playlist PlaylistURL, apiKey string) (CourseInfo, error) {
	var pageHTML string
	var videos []VideoInfo
	err := chromedp.Run(ctx,
		chromedp.Navigate("https://www.youtube.com"+playlist.URL),
		chromedp.Sleep(2*time.Second),
		scrollPlaylistVideos(&videos),
		chromedp.OuterHTML("html", &pageHTML),
	)
	if err != nil {
		return CourseInfo{}, err
	}

	// Clean HTML before sending to Gemini
	cleanedHTML := cleanHTML(pageHTML)
	log.Printf("Original HTML size: %d, Cleaned HTML size: %d", len(pageHTML), len(cleanedHTML))

	courseInfo, err := extractCourseMetadata(apiKey, cleanedHTML)
	if err != nil {
		return CourseInfo{}, err
	}

	courseInfo.URL = playlist.URL
	for i := range courseInfo.Videos {
		courseInfo.Videos[i].Position = videos[i].Position
	}
	return courseInfo, nil
}

func WriteCoursesToCSV(courses []CourseInfo, filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return fmt.Errorf("failed to create file: %w", err)
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	header := []string{"CourseURL", "CourseTitle", "Position", "VideoURL", "VideoTitle", "ViewCount", "Taxonomy"}
	if err := writer.Write(header); err != nil {
		return fmt.Errorf("failed to write header: %w", err)
	}

	for _, course := range courses {
		for _, video := range course.Videos {
			row := []string{
				course.URL,
				course.Title,
				fmt.Sprintf("%d", video.Position),
				video.URL,
				video.Title,
				fmt.Sprintf("%d", video.ViewCount),
				video.Taxonomy,
			}
			if err := writer.Write(row); err != nil {
				return fmt.Errorf("failed to write row: %w", err)
			}
		}
	}
	return nil
}
