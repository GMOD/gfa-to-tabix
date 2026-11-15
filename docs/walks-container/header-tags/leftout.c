#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_ID (1ULL << 31)
#define NAME_MAX_LEN 4096

static uint64_t *ref_bits, *zero_bits;
static const char *ref_sample;
static FILE *pending, *names_out;
static uint64_t lines_total, lines_ref, lines_no_step, lines_placed, lines_pending;
static uint64_t pending_ids, segments, zero_segments, segments_after_paths, ref_after_other;
static int saw_path, saw_other_path;

static inline int has(const uint64_t *bits, uint64_t id) {
  return (bits[id >> 6] >> (id & 63)) & 1;
}
static inline void set(uint64_t *bits, uint64_t id) {
  bits[id >> 6] |= 1ULL << (id & 63);
}
static void die(const char *why) {
  fprintf(stderr, "leftout: %s at input line %llu\n", why,
          (unsigned long long)(lines_total + segments + 1));
  exit(2);
}
static int skip_line(int c) {
  while (c != '\n' && c != EOF) c = getc_unlocked(stdin);
  return c;
}
static int read_field(char *into, size_t cap, size_t *len) {
  size_t n = 0;
  int c = getc_unlocked(stdin);
  while (c != '\t' && c != '\n' && c != EOF) {
    if (n + 1 < cap) into[n++] = (char)c;
    c = getc_unlocked(stdin);
  }
  into[n] = 0;
  if (len) *len = n;
  return c;
}

static uint32_t *held;
static size_t held_n, held_cap;
static void hold(uint32_t id) {
  if (held_n == held_cap) {
    held_cap = held_cap ? held_cap * 2 : 1 << 16;
    held = realloc(held, held_cap * sizeof *held);
    if (!held) die("out of memory holding a line's steps");
  }
  held[held_n++] = id;
}

static void finish_path(const char *name, int is_ref, int touched, uint64_t steps) {
  lines_total++;
  if (is_ref) {
    lines_ref++;
    if (saw_other_path) ref_after_other++;
  } else {
    saw_other_path = 1;
    if (steps == 0) {
      lines_no_step++;
    } else if (touched) {
      lines_placed++;
    } else {
      uint32_t name_len = (uint32_t)strlen(name);
      uint64_t n = held_n;
      lines_pending++;
      pending_ids += n;
      if (pending_ids > (1ULL << 35)) die("pending steps past 2^35: reference lines come too late for one pass");
      fwrite(&name_len, sizeof name_len, 1, pending);
      fwrite(name, 1, name_len, pending);
      fwrite(&n, sizeof n, 1, pending);
      fwrite(held, sizeof *held, held_n, pending);
    }
  }
}

/* steps as W writes them (>12<34) or as P does (12+,34-); returns the char that ended the field */
static int read_steps(const char *name, int is_ref) {
  int c = getc_unlocked(stdin), touched = 0;
  uint64_t steps = 0;
  held_n = 0;
  while (c != '\t' && c != '\n' && c != EOF) {
    if (c >= '0' && c <= '9') {
      uint64_t id = 0;
      while (c >= '0' && c <= '9') {
        id = id * 10 + (uint64_t)(c - '0');
        c = getc_unlocked(stdin);
      }
      if (id >= MAX_ID) die("node id at or past 2^31");
      if (is_ref) {
        set(ref_bits, id);
      } else if (!has(zero_bits, id)) {
        steps++;
        if (has(ref_bits, id)) {
          touched = 1;
          finish_path(name, 0, 1, steps);
          return skip_line(c);
        }
        hold((uint32_t)id);
      }
    } else if (c == '>' || c == '<' || c == '+' || c == '-' || c == ',' || c == '*') {
      c = getc_unlocked(stdin);
    } else {
      die("a step that is not an integer id");
    }
  }
  finish_path(name, is_ref, touched, is_ref ? 1 : steps);
  return skip_line(c);
}

int main(int argc, char **argv) {
  if (argc != 4) {
    fprintf(stderr, "usage: leftout REF_SAMPLE pending.tmp names.out < graph.gfa\n");
    return 2;
  }
  ref_sample = argv[1];
  size_t ref_len = strlen(ref_sample);
  ref_bits = calloc(MAX_ID / 64, sizeof *ref_bits);
  zero_bits = calloc(MAX_ID / 64, sizeof *zero_bits);
  pending = fopen(argv[2], "w+b");
  names_out = fopen(argv[3], "w");
  if (!ref_bits || !zero_bits || !pending || !names_out) die("setup failed");
  static char inbuf[1 << 24];
  setvbuf(stdin, inbuf, _IOFBF, sizeof inbuf);
  char a[NAME_MAX_LEN], b[NAME_MAX_LEN], name[3 * NAME_MAX_LEN];

  int c = getc_unlocked(stdin);
  while (c != EOF) {
    int type = c;
    c = getc_unlocked(stdin);
    if (type == '\n') {
      continue;
    } else if (c != '\t') {
      c = skip_line(c);
    } else if (type == 'S') {
      size_t id_len, seq_len = 0;
      if (saw_path) segments_after_paths++;
      segments++;
      c = read_field(a, sizeof a, &id_len);
      uint64_t id = 0;
      for (size_t i = 0; i < id_len; i++) {
        if (a[i] < '0' || a[i] > '9') die("a segment id that is not an integer");
        id = id * 10 + (uint64_t)(a[i] - '0');
      }
      if (id >= MAX_ID) die("segment id at or past 2^31");
      int first = EOF, star = 0;
      if (c == '\t') {
        c = getc_unlocked(stdin);
        first = c;
        while (c != '\t' && c != '\n' && c != EOF) {
          seq_len++;
          c = getc_unlocked(stdin);
        }
        star = seq_len == 1 && first == '*';
      }
      uint64_t length = star ? 0 : seq_len;
      int stated = 0;
      while (c == '\t') {
        c = read_field(b, sizeof b, NULL);
        if (star && !strncmp(b, "LN:i:", 5)) {
          length = strtoull(b + 5, NULL, 10);
          stated = 1;
        }
      }
      (void)stated;
      if (length == 0) {
        set(zero_bits, id);
        zero_segments++;
      }
      c = skip_line(c);
    } else if (type == 'W') {
      saw_path = 1;
      c = read_field(a, sizeof a, NULL);
      int is_ref = !strcmp(a, ref_sample);
      size_t n = (size_t)snprintf(name, sizeof name, "%s", a);
      for (int f = 0; f < 4 && c == '\t'; f++) {
        c = read_field(b, sizeof b, NULL);
        n += (size_t)snprintf(name + n, sizeof name - n, f < 2 ? "#%s" : f == 2 ? ":%s" : "-%s", b);
      }
      c = c == '\t' ? read_steps(name, is_ref) : (finish_path(name, is_ref, 0, 0), skip_line(c));
    } else if (type == 'P') {
      saw_path = 1;
      c = read_field(name, sizeof name, NULL);
      int is_ref = !strncmp(name, ref_sample, ref_len) && (name[ref_len] == '#' || name[ref_len] == 0);
      c = c == '\t' ? read_steps(name, is_ref) : (finish_path(name, is_ref, 0, 0), skip_line(c));
    } else {
      c = skip_line(c);
    }
    if (c == '\n') c = getc_unlocked(stdin);
  }

  uint64_t leftout = 0, rescued = 0;
  rewind(pending);
  for (uint64_t k = 0; k < lines_pending; k++) {
    uint32_t name_len;
    uint64_t n;
    if (fread(&name_len, sizeof name_len, 1, pending) != 1) die("pending file cut short");
    if (name_len >= sizeof name || fread(name, 1, name_len, pending) != name_len) die("pending name cut short");
    name[name_len] = 0;
    if (fread(&n, sizeof n, 1, pending) != 1) die("pending count cut short");
    int touched = 0;
    for (uint64_t i = 0; i < n; i++) {
      uint32_t id;
      if (fread(&id, sizeof id, 1, pending) != 1) die("pending steps cut short");
      touched |= has(ref_bits, id);
    }
    if (touched) {
      rescued++;
    } else {
      leftout++;
      fprintf(names_out, "%s\t%llu\n", name, (unsigned long long)n);
    }
  }
  printf("reference\t%s\n", ref_sample);
  printf("segments\t%llu\n", (unsigned long long)segments);
  printf("segments_of_0bp\t%llu\n", (unsigned long long)zero_segments);
  printf("segments_after_first_path\t%llu\n", (unsigned long long)segments_after_paths);
  printf("path_lines\t%llu\n", (unsigned long long)lines_total);
  printf("reference_lines\t%llu\n", (unsigned long long)lines_ref);
  printf("reference_lines_after_another_line\t%llu\n", (unsigned long long)ref_after_other);
  printf("lines_with_no_step\t%llu\n", (unsigned long long)lines_no_step);
  printf("lines_touching_reference_when_read\t%llu\n", (unsigned long long)lines_placed);
  printf("lines_held_then_found_touching\t%llu\n", (unsigned long long)rescued);
  printf("leftout\t%llu\n", (unsigned long long)leftout);
  return 0;
}
