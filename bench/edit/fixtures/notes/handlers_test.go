package notes

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func do(t *testing.T, srv http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	return rec
}

func TestCreateAndGet(t *testing.T) {
	srv := NewServer(NewStore())
	rec := do(t, srv, "POST", "/notes", `{"title":"a","body":"b"}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: %d %s", rec.Code, rec.Body)
	}
	rec = do(t, srv, "GET", "/notes/1", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"title":"a"`) {
		t.Fatalf("get: %d %s", rec.Code, rec.Body)
	}
	if rec := do(t, srv, "GET", "/notes/42", ""); rec.Code != http.StatusNotFound {
		t.Fatalf("missing: %d", rec.Code)
	}
}
