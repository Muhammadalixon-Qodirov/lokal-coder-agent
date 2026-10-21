package notes

import "time"

// Note — foydalanuvchi qaydi.
type Note struct {
	ID        int       `json:"id"`
	Title     string    `json:"title"`
	Body      string    `json:"body"`
	CreatedAt time.Time `json:"created_at"`
}

// CreateNoteRequest — POST /notes so'rov tanasi.
type CreateNoteRequest struct {
	Title string `json:"title"`
	Body  string `json:"body"`
}
