package main

import (
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/joho/godotenv"
	"github.com/jorgoose/mit-ocw-youtube/scraper"
)

func main() {
	// Load .env file
	if err := godotenv.Load(); err != nil {
		log.Fatal("Error loading .env file")
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
