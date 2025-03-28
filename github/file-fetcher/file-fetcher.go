package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/google/go-github/v70/github"
	"gopkg.in/yaml.v3"
)

const configFilePath = "./config.yaml"

type Config struct {
	Search Search `yaml:"search"`
	Data   Data   `yaml:"data"`
	Token  string
}

type Data struct {
	OutputDir string `yaml:"output_dir"`
	IndexFile string `yaml:"index_file"`
}

type Search struct {
	Query   string `yaml:"query"`
	PerPage int    `yaml:"per_page"`
}

type File struct {
	URL  string
	Repo string
	Path string
	Name string
	Org  string
}

func main() {

	// 1. Load config
	fmt.Println("Loading config...")
	config, err := loadConfig()
	if err != nil {
		log.Fatalf("couldn't initiate config: %v", err)
	}

	client := github.NewClient(nil).WithAuthToken(config.Token)

	// Search files
	fmt.Println("Searching files...")
	config, err = loadConfig()
	searchResults, err := searchCode(client, config)
	if err != nil {
		log.Fatalf("code search failed: %v", err)
	}

	// Download Files
	fmt.Println("Downloading files...")
	err = downloadFiles(client, config, searchResults)
	if err != nil {
		log.Fatalf("file download failed: %v", err)
	}
	// 4. download files
}

func loadConfig() (*Config, error) {
	configFile, err := os.ReadFile(configFilePath)
	if err != nil {
		return nil, err
	}

	var config Config
	err = yaml.Unmarshal(configFile, &config)
	if err != nil {
		return nil, err
	}

	config.Token = os.Getenv("GH_TOKEN")
	if config.Token == "" {
		return nil, fmt.Errorf("GH_TOKEN env is not set")
	}

	_, err = os.ReadDir(config.Data.OutputDir)
	if err != nil {
		return nil, fmt.Errorf("Output dir '%s' doesn't exist", config.Data.OutputDir)
	}

	return &config, nil

}

func searchCode(c *github.Client, conf *Config) ([]File, error) {

	files := []File{}

	ctx := context.Context(context.Background())
	opts := &github.SearchOptions{
		ListOptions: github.ListOptions{
			Page:    0,
			PerPage: conf.Search.PerPage,
		},
	}

	for {
		sr, r, err := c.Search.Code(ctx, conf.Search.Query, opts)
		// Pause on RateLimitError, fail on unexpected response
		if err != nil {
			if _, ok := err.(*github.RateLimitError); ok {
				log.Println("hit rate limit, waiting 5 seconds")
				time.Sleep(5 * time.Second)
				continue
			} else if r.Status != "200 OK" {
				log.Fatalf("unexpected response code: %v", r.Status)
			}
		}

		for _, result := range sr.CodeResults {

			file := File{
				Repo: result.GetRepository().GetName(),
				URL:  result.GetHTMLURL(),
				Path: result.GetPath(),
				Name: result.GetName(),
				Org:  strings.Split(result.Repository.GetFullName(), "/")[0],
			}
			files = append(files, file)
		}
		if r.NextPage == 0 {
			break
		}
		opts.Page = r.NextPage
	}
	return files, nil

}

func downloadFiles(c *github.Client, conf *Config, files []File) error {

	ctx := context.Context(context.Background())
	totalNumber := len(files)
	for i, file := range files {
		fmt.Printf("\rProgress: %d/%d", i, totalNumber)
		fileContent, _, _, err := c.Repositories.GetContents(ctx, file.Org, file.Repo, file.Path, nil)
		if err != nil {
			return err
		}
		content, err := fileContent.GetContent()
		if err != nil {
			return err
		}
		filePathSanitized := strings.ReplaceAll(file.Path, "/", "_")
		filePath := conf.Data.OutputDir + file.Repo + "_" + filePathSanitized
		err = os.WriteFile(filePath, []byte(content), 0677)
		if err != nil {
			return err
		}
	}

	return nil
}
