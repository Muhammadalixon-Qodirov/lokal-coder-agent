package notes

import (
	"sync"
	"time"
)

// Store — xotiradagi qaydlar ombori.
type Store struct {
	mu     sync.Mutex
	nextID int
	notes  map[int]Note
	now    func() time.Time
}

func NewStore() *Store {
	return &Store{nextID: 1, notes: map[int]Note{}, now: time.Now}
}

func (s *Store) Create(title, body string) Note {
	s.mu.Lock()
	defer s.mu.Unlock()
	n := Note{ID: s.nextID, Title: title, Body: body, CreatedAt: s.now()}
	s.notes[n.ID] = n
	s.nextID++
	return n
}

func (s *Store) Get(id int) (Note, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	n, ok := s.notes[id]
	return n, ok
}

func (s *Store) List() []Note {
	s.mu.Lock()
	defer s.mu.Unlock()
	out := make([]Note, 0, len(s.notes))
	for _, n := range s.notes {
		out = append(out, n)
	}
	return out
}
