package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/joho/godotenv"
	"github.com/jorgoose/mit-ocw-youtube/scraper"
)

func main() {
	// Load .env file if it exists (won't error in GitHub Actions)
	_ = godotenv.Load()

	// Check if required environment variable is set
	if os.Getenv("GEMINI_API_KEY") == "" {
		log.Fatal("GEMINI_API_KEY environment variable must be set")
	}

	// Check for Kaggle credentials
	if os.Getenv("KAGGLE_USERNAME") == "" || os.Getenv("KAGGLE_KEY") == "" {
		log.Fatal("KAGGLE_USERNAME and KAGGLE_KEY environment variables must be set")
	}

	// Get course info
	courses, err := scraper.GetCourseInfo()
	if err != nil {
		log.Fatal(err)
	}

	// Print results as JSON
	jsonData, err := json.MarshalIndent(courses, "", "  ")
	if err != nil {
		log.Fatal(err)
	}
	log.Printf("Course data:\n%s", jsonData)

	// Save to CSV
	filename := fmt.Sprintf("mit_courses_%s.csv", time.Now().Format("2006-01-02_150405"))
	if err := scraper.WriteCoursesToCSV(courses, filename); err != nil {
		log.Fatal(err)
	}
	log.Printf("Data saved to %s", filename)
}
