from coder.indexer.langs import extract


def _syms(facts):
    return {(s.qualname, s.kind) for s in facts.symbols}


def _refs(facts, kind):
    out = set()
    for r in facts.refs:
        if r.kind == kind:
            src = facts.symbols[r.src].qualname if r.src is not None else None
            out.add((src, r.dst_name))
    return out


def test_python():
    src = b'''
import os
from django.db import models
from rest_framework import serializers as s

class Card(models.Model):
    title = models.CharField(max_length=100)

    def archive(self):
        self.is_archived = True
        self.save()

def helper(x):
    return Card.objects.filter(x=x)
'''
    f = extract("python", src)
    assert _syms(f) == {("Card", "class"), ("Card.archive", "method"), ("helper", "function")}
    assert ("Card", "Model") in _refs(f, "inherits")
    assert ("Card.archive", "save") in _refs(f, "calls")
    assert ("helper", "filter") in _refs(f, "calls")
    assert {d for _, d in _refs(f, "imports")} == {"os", "django.db", "rest_framework"}
    archive = next(s for s in f.symbols if s.name == "archive")
    assert archive.signature == "def archive(self)"
    assert (archive.start_line, archive.end_line) == (9, 11)


def test_go():
    src = b'''package api

import (
    "net/http"
    "encoding/json"
)

type Server struct{ db *DB }

type Store interface{ Get(id int) error }

func (s *Server) Login(w http.ResponseWriter, r *http.Request) {
    var req LoginReq
    json.NewDecoder(r.Body).Decode(&req)
    validate(req)
}

func validate(r LoginReq) error { return nil }
'''
    f = extract("go", src)
    assert _syms(f) == {
        ("Server", "struct"), ("Store", "interface"), ("Server.Login", "method"), ("validate", "function"),
    }
    assert ("Server.Login", "validate") in _refs(f, "calls")
    assert ("Server.Login", "Decode") in _refs(f, "calls")
    assert {d for _, d in _refs(f, "imports")} == {"net/http", "encoding/json"}


def test_typescript():
    src = b'''import axios from "axios";
import { User } from './types';

export interface Props { id: number }

export class ProfileApi extends BaseApi implements Api {
  async getProfile(id: number): Promise<User> {
    const r = await axios.get(`/api/profile/${id}`);
    return mapUser(r.data);
  }
}

export const mapUser = (d: any): User => new User(d);

export function ProfilePage({ id }: Props) {
  return fetchIt(id);
}
'''
    f = extract("typescript", src)
    assert _syms(f) == {
        ("Props", "interface"), ("ProfileApi", "class"), ("ProfileApi.getProfile", "method"),
        ("mapUser", "function"), ("ProfilePage", "function"),
    }
    calls = _refs(f, "calls")
    assert ("ProfileApi.getProfile", "get") in calls
    assert ("ProfileApi.getProfile", "mapUser") in calls
    assert ("mapUser", "User") in calls
    assert {d for _, d in _refs(f, "imports")} == {"axios", "./types"}
    assert {d for _, d in _refs(f, "inherits")} >= {"BaseApi", "Api"}


def test_dart():
    src = b'''import 'package:dio/dio.dart';

class ProfileApi extends Base {
  final Dio dio;
  ProfileApi(this.dio);

  Future<User> getProfile(int id) async {
    final r = await dio.get('/api/profile/$id');
    return User.fromJson(r.data);
  }
}

void main() {
  runApp(MyApp());
}
'''
    f = extract("dart", src)
    syms = _syms(f)
    assert ("ProfileApi", "class") in syms
    assert ("ProfileApi.getProfile", "method") in syms
    assert ("main", "function") in syms
    calls = _refs(f, "calls")
    assert ("ProfileApi.getProfile", "get") in calls
    assert ("ProfileApi.getProfile", "fromJson") in calls
    assert ("main", "runApp") in calls
    assert ("ProfileApi", "Base") in _refs(f, "inherits")
    assert {d for _, d in _refs(f, "imports")} == {"package:dio/dio.dart"}
    gp = next(s for s in f.symbols if s.name == "getProfile")
    assert gp.end_line == 10  # body qo'shni node'dan olingan
