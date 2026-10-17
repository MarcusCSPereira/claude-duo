// Local build/content records, macOS 12+. Never runs app/profile code.
// A user-owned record detects drift, not an attacker able to rewrite the record.
#include <CommonCrypto/CommonDigest.h>
#include <CoreFoundation/CoreFoundation.h>
#include <sys/acl.h>
#include <sys/stat.h>
#include <sys/xattr.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define MARKER "Contents/Resources/mcd-build-id"
struct hashes { unsigned char full[32], unchanged[32]; };
struct walk { const char *root; dev_t device; bool source, icon; size_t entries; };
static void fail(const char *message) { fprintf(stderr, "integrity: %s\n", message); exit(1); }
static void syserr(const char *message) { fprintf(stderr, "integrity: %s: %s\n", message, strerror(errno)); exit(1); }
static struct stat info(int fd) { struct stat s; if (fstat(fd, &s)) syserr("cannot inspect descriptor"); return s; }
static bool same(struct stat a, struct stat b) {
    return a.st_dev == b.st_dev && a.st_ino == b.st_ino && a.st_mode == b.st_mode && a.st_uid == b.st_uid &&
        a.st_gid == b.st_gid && a.st_nlink == b.st_nlink && a.st_size == b.st_size && a.st_flags == b.st_flags &&
        a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec && a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec &&
        a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec && a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec;
}
static void acl_check(int fd) {
    acl_t acl = acl_get_fd_np(fd, ACL_TYPE_EXTENDED);
    if (!acl) { if (errno == ENOENT) return; syserr("cannot inspect ACL"); }
    acl_entry_t entry; int rc = acl_get_entry(acl, ACL_FIRST_ENTRY, &entry);
    while (rc == 0) {
        acl_tag_t tag;
        if (acl_get_tag_type(entry, &tag) || tag != ACL_EXTENDED_DENY) fail("custom allow/unknown ACL");
        rc = acl_get_entry(acl, ACL_NEXT_ENTRY, &entry);
    }
    int saved = errno; acl_free(acl);
    if (rc != -1 || saved != EINVAL) fail("unknown ACL enumeration result");
}
static void metadata(int fd, struct stat s, struct walk *walk) {
    if ((s.st_uid != getuid() && !(walk->source && s.st_uid == 0)) || s.st_dev != walk->device || (s.st_mode & 0022))
        fail("foreign, writable or cross-device app entry");
    if (!S_ISREG(s.st_mode) && !S_ISDIR(s.st_mode)) fail("unsupported app entry");
    if (S_ISREG(s.st_mode) && s.st_nlink != 1) fail("hardlinked app file");
    acl_check(fd);
}
static void update(CC_SHA256_CTX *c, const void *p, size_t length) {
    if (length > UINT32_MAX || !CC_SHA256_Update(c, p, (CC_LONG)length)) fail("hash update failed");
}
static void number(CC_SHA256_CTX *c, uint64_t n) {
    unsigned char bytes[8]; for (int i = 7; i >= 0; i--) { bytes[i] = (unsigned char)n; n >>= 8; } update(c, bytes, 8);
}
static void start(CC_SHA256_CTX *c, const char *type, mode_t mode) {
    if (!CC_SHA256_Init(c)) fail("hash initialization failed");
    update(c, "MCD_TREE_2", 10); update(c, type, 1); number(c, mode & 07777);
}
static void finish(CC_SHA256_CTX *c, unsigned char digest[32]) { if (!CC_SHA256_Final(digest, c)) fail("hash finalization failed"); }
static void hex(const unsigned char bytes[32], char text[65]) { for (size_t i = 0; i < 32; i++) snprintf(text + i * 2, 3, "%02x", bytes[i]); }
static int ordered(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }
static char **names(int fd, size_t *count) {
    int copy = dup(fd); if (copy < 0) syserr("cannot duplicate directory");
    DIR *dir = fdopendir(copy); if (!dir) syserr("cannot enumerate directory");
    rewinddir(dir); *count = 0; size_t capacity = 0; char **items = NULL;
    for (;;) {
        errno = 0; struct dirent *entry = readdir(dir);
        if (!entry) { if (errno) syserr("directory read failed"); break; }
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        if (*count >= 1000000) fail("directory entry limit exceeded");
        if (*count == capacity) {
            capacity = capacity ? capacity * 2 : 32;
            char **grown = realloc(items, capacity * sizeof(*items)); if (!grown) syserr("allocation failed"); items = grown;
        }
        items[*count] = strdup(entry->d_name); if (!items[*count]) syserr("allocation failed"); (*count)++;
    }
    if (closedir(dir)) syserr("cannot close enumeration");
    if (*count) qsort(items, *count, sizeof(*items), ordered); return items;
}
static void security_attributes(int fd, CC_SHA256_CTX *c) {
    ssize_t length = flistxattr(fd, NULL, 0, 0);
    if (length < 0 || length > 1024 * 1024) fail("cannot bound extended attribute list");
    char *buffer = malloc((size_t)length + 1); if (!buffer) syserr("allocation failed");
    if (flistxattr(fd, buffer, (size_t)length, 0) != length) fail("attribute list changed");
    char **selected = calloc((size_t)length + 1, sizeof(char *)); if (!selected) syserr("allocation failed");
    size_t count = 0, offset = 0;
    while (offset < (size_t)length) {
        size_t size = strnlen(buffer + offset, (size_t)length - offset);
        if (!size || size == (size_t)length - offset) fail("invalid attribute list");
        char *name = buffer + offset;
        if (!strncmp(name, "com.apple.cs.", 13) || !strcmp(name, "com.apple.ResourceFork")) selected[count++] = name;
        offset += size + 1;
    }
    if (count) qsort(selected, count, sizeof(*selected), ordered);
    number(c, count);
    for (size_t i = 0; i < count; i++) {
        ssize_t size = fgetxattr(fd, selected[i], NULL, 0, 0, 0);
        if (size < 0 || size > 16 * 1024 * 1024) fail("cannot bound security/resource-fork attribute");
        unsigned char *value = malloc((size_t)size + 1); if (!value) syserr("allocation failed");
        if (fgetxattr(fd, selected[i], value, (size_t)size, 0, 0) != size) fail("attribute changed during read");
        number(c, strlen(selected[i])); update(c, selected[i], strlen(selected[i])); number(c, (uint64_t)size); update(c, value, (size_t)size); free(value);
    }
    free(selected); free(buffer);
}
static bool mutable(const char *path, bool icon) {
    return !strcmp(path, "Contents/Info.plist") || !strcmp(path, "Contents/MacOS/Claude") ||
        !strcmp(path, "Contents/MacOS/launcher") || !strcmp(path, "Contents/_CodeSignature/CodeResources") ||
        !strcmp(path, "Contents/_CodeSignature/CodeDirectory") || !strcmp(path, "Contents/_CodeSignature/CodeRequirements") ||
        !strcmp(path, "Contents/_CodeSignature/CodeSignature") ||
        !strcmp(path, MARKER) || (icon && !strcmp(path, "Contents/Resources/appicon.icns"));
}
static bool inside(const char *root, const char *path) { size_t length = strlen(root); return !strncmp(root, path, length) && path[length] == '/'; }
static void file_data(int fd, CC_SHA256_CTX *c, CC_SHA256_CTX *fixed, off_t expected) {
    unsigned char bytes[65536]; uint64_t total = 0;
    for (;;) {
        ssize_t count = read(fd, bytes, sizeof(bytes));
        if (count < 0 && errno == EINTR) continue;
        if (count < 0) syserr("cannot read app file"); if (!count) break;
        total += (uint64_t)count; if (total > (uint64_t)expected) fail("app file grew"); update(c, bytes, (size_t)count); update(fixed, bytes, (size_t)count);
    }
    if (total != (uint64_t)expected) fail("app file shrank");
}
static struct hashes visit(int fd, const char *path, struct walk *walk, unsigned depth) {
    if (depth > 128 || ++walk->entries > 1000000) fail("tree depth/entry limit exceeded");
    struct stat before = info(fd); metadata(fd, before, walk);
    CC_SHA256_CTX full, fixed; struct hashes result;
    start(&full, S_ISDIR(before.st_mode) ? "D" : "F", before.st_mode);
    start(&fixed, S_ISDIR(before.st_mode) ? "D" : "F", before.st_mode & 0700);
    security_attributes(fd, &full);
    security_attributes(fd, &fixed);
    if (S_ISREG(before.st_mode)) {
        number(&full, (uint64_t)before.st_size); number(&fixed, (uint64_t)before.st_size); file_data(fd, &full, &fixed, before.st_size);
        finish(&full, result.full); finish(&fixed, result.unchanged);
    } else {
        size_t count; char **items = names(fd, &count);
        for (size_t i = 0; i < count; i++) {
            char child_path[PATH_MAX];
            int length = snprintf(child_path, sizeof(child_path), "%s%s%s", path, *path ? "/" : "", items[i]);
            if (length < 0 || (size_t)length >= sizeof(child_path)) fail("app path too long");
            struct stat named; if (fstatat(fd, items[i], &named, AT_SYMLINK_NOFOLLOW)) syserr("cannot inspect app child");
            struct hashes child;
            if (S_ISLNK(named.st_mode)) {
                if (named.st_uid != getuid() && !(walk->source && named.st_uid == 0)) fail("foreign symlink");
                char link[PATH_MAX], absolute[PATH_MAX], resolved[PATH_MAX];
                ssize_t size = readlinkat(fd, items[i], link, sizeof(link));
                if (size <= 0 || (size_t)size >= sizeof(link) || link[0] == '/') fail("invalid/absolute bundle symlink");
                link[size] = '\0';
                length = snprintf(absolute, sizeof(absolute), "%s/%s", walk->root, child_path);
                if (length < 0 || (size_t)length >= sizeof(absolute) || !realpath(absolute, resolved) || !inside(walk->root, resolved)) fail("escaping, dangling or cyclic bundle symlink");
                CC_SHA256_CTX h; start(&h, "L", 0); number(&h, (uint64_t)size); update(&h, link, (size_t)size);
                finish(&h, child.full); memcpy(child.unchanged, child.full, 32);
            } else {
                if (!S_ISREG(named.st_mode) && !S_ISDIR(named.st_mode)) fail("special app file");
                int next = openat(fd, items[i], O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
                if (next < 0 || !same(named, info(next))) fail("app child changed during open");
                child = visit(next, child_path, walk, depth + 1); close(next);
            }
            struct stat after; if (fstatat(fd, items[i], &after, AT_SYMLINK_NOFOLLOW) || !same(named, after)) fail("named app child changed");
            number(&full, strlen(items[i])); update(&full, items[i], strlen(items[i])); update(&full, child.full, 32);
            if (!mutable(child_path, walk->icon)) { number(&fixed, strlen(items[i])); update(&fixed, items[i], strlen(items[i])); update(&fixed, child.unchanged, 32); }
            free(items[i]);
        }
        free(items); finish(&full, result.full); finish(&fixed, result.unchanged);
    }
    if (!same(before, info(fd))) fail("app changed during tree observation"); return result;
}
static int root(const char *path, bool source, bool private) {
    if (path[0] != '/') fail("absolute path required");
    int fd = open(path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW_ANY | O_CLOEXEC);
    if (fd < 0) syserr("cannot open root without symlinks");
    struct stat s = info(fd); struct walk walk = {.source = source, .device = s.st_dev}; metadata(fd, s, &walk);
    if (private && (s.st_mode & 07777) != 0700) fail("record directory must be private"); return fd;
}
static struct hashes tree(int fd, const char *path, bool source, bool icon) {
    struct walk walk = {.root = path, .device = info(fd).st_dev, .source = source, .icon = icon, .entries = 0};
    struct hashes result = visit(fd, "", &walk, 0);
    int named = root(path, source, false); if (!same(info(fd), info(named))) fail("app root path changed"); close(named); return result;
}
static bool uuid(const char *id) {
    if (strlen(id) != 36) return false;
    for (size_t i = 0; i < 36; i++) if ((i == 8 || i == 13 || i == 18 || i == 23) ? id[i] != '-' : !strchr("0123456789abcdef", id[i])) return false;
    return true;
}
static bool digest(const char *text) { return strlen(text) == 64 && strspn(text, "0123456789abcdef") == 64; }
static size_t read_small(int parent, const char *path, char *buffer, size_t limit) {
    int fd = openat(parent, path, O_RDONLY | O_NOFOLLOW_ANY | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) syserr("missing or linked build record/marker");
    struct stat before = info(fd);
    if (!S_ISREG(before.st_mode) || before.st_uid != getuid() || before.st_nlink != 1 || (before.st_mode & 0022) || before.st_size <= 0 || (uint64_t)before.st_size >= limit) fail("unsafe build record/marker");
    if (!strcmp(path, "record.txt") && (before.st_mode & 07777) != 0600) fail("build record must be mode 0600");
    acl_check(fd); size_t total = 0;
    while (total < limit) {
        ssize_t n = read(fd, buffer + total, limit - total);
        if (n < 0 && errno == EINTR) continue; if (n < 0) syserr("record read failed"); if (!n) break; total += (size_t)n;
    }
    if (total != (size_t)before.st_size || !same(before, info(fd))) fail("record changed during read");
    buffer[total] = '\0'; close(fd); return total;
}
static void marker(int app, char id[37]) {
    char bytes[64]; size_t length = read_small(app, MARKER, bytes, sizeof(bytes) - 1);
    if (length != 37 || bytes[36] != '\n') fail("invalid build marker"); memcpy(id, bytes, 36); id[36] = '\0'; if (!uuid(id)) fail("invalid build UUID");
}
static CFMutableDictionaryRef CreatePlist(int app) {
    int fd = openat(app, "Contents/Info.plist", O_RDONLY | O_NOFOLLOW_ANY | O_CLOEXEC);
    if (fd < 0) syserr("cannot open Info.plist"); struct stat before = info(fd);
    if (!S_ISREG(before.st_mode) || before.st_size <= 0 || before.st_size > 16 * 1024 * 1024) fail("invalid Info.plist size/type");
    unsigned char *bytes = malloc((size_t)before.st_size); if (!bytes) syserr("allocation failed"); size_t total = 0;
    while (total < (size_t)before.st_size) {
        ssize_t n = read(fd, bytes + total, (size_t)before.st_size - total);
        if (n < 0 && errno == EINTR) continue; if (n <= 0) fail("partial plist read"); total += (size_t)n;
    }
    if (!same(before, info(fd))) fail("plist changed during read"); close(fd);
    CFDataRef data = CFDataCreate(NULL, bytes, (CFIndex)total); free(bytes); if (!data) fail("plist allocation failed");
    CFPropertyListRef value = CFPropertyListCreateWithData(NULL, data, kCFPropertyListMutableContainersAndLeaves, NULL, NULL); CFRelease(data);
    if (!value || CFGetTypeID(value) != CFDictionaryGetTypeID()) fail("Info.plist must be a dictionary"); return (CFMutableDictionaryRef)value;
}
static void set_string(CFMutableDictionaryRef d, CFStringRef key, const char *text) {
    CFStringRef value = CFStringCreateWithCString(NULL, text, kCFStringEncodingUTF8); if (!value) fail("invalid metadata string"); CFDictionarySetValue(d, key, value); CFRelease(value);
}
static void planned_metadata(int source, int app, const char *name, const char *bid, bool icon) {
    CFMutableDictionaryRef expected = CreatePlist(source), actual = CreatePlist(app);
    if (!CFEqual(CFDictionaryGetValue(expected, CFSTR("CFBundleIdentifier")) ?: CFSTR(""), CFSTR("com.anthropic.claudefordesktop"))) fail("unexpected source bundle identity");
    char display[96]; int size = snprintf(display, sizeof(display), "Claude %s", name); if (size < 0 || (size_t)size >= sizeof(display)) fail("instance name too long");
    set_string(expected, CFSTR("CFBundleIdentifier"), bid); set_string(expected, CFSTR("CFBundleDisplayName"), display); set_string(expected, CFSTR("CFBundleExecutable"), "launcher");
    CFDictionaryRemoveValue(expected, CFSTR("CFBundleURLTypes")); CFDictionaryRemoveValue(expected, CFSTR("NSUserActivityTypes"));
    if (icon) { set_string(expected, CFSTR("CFBundleIconFile"), "appicon"); CFDictionaryRemoveValue(expected, CFSTR("CFBundleIconName")); }
    if (!CFEqual(expected, actual)) fail("Info.plist differs beyond planned changes"); CFRelease(expected); CFRelease(actual);
}
static void sync_fd(int fd) { int rc; do { rc = fsync(fd); } while (rc && errno == EINTR); if (rc) syserr("record sync failed"); }
static void record_create(int records, const char *id, const char *binding, struct hashes source, struct hashes app) {
    if (mkdirat(records, id, 0700)) syserr("record UUID already exists or cannot be created");
    int directory = openat(records, id, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC); if (directory < 0) syserr("cannot open record directory");
    char source_hex[65], fixed_hex[65], app_hex[65], buffer[400]; hex(source.full, source_hex); hex(source.unchanged, fixed_hex); hex(app.full, app_hex);
    int length = snprintf(buffer, sizeof(buffer), "MCD_INTEGRITY 1\nconfig %s\nsource %s\nunchanged %s\nbundle %s\n", binding, source_hex, fixed_hex, app_hex);
    if (length <= 0 || (size_t)length >= sizeof(buffer)) fail("record serialization failed");
    int fd = openat(directory, "record.txt", O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600); if (fd < 0) syserr("cannot create exclusive build record");
    size_t written = 0; while (written < (size_t)length) { ssize_t n = write(fd, buffer + written, (size_t)length - written); if (n < 0 && errno == EINTR) continue; if (n <= 0) syserr("record write failed"); written += (size_t)n; }
    sync_fd(fd); if (close(fd)) syserr("record close failed"); sync_fd(directory); sync_fd(records); close(directory);
}
static void field(const char **cursor, const char *end, const char *label, char value[65]) {
    size_t length = strlen(label);
    if ((size_t)(end - *cursor) < length + 65 || memcmp(*cursor, label, length)) fail("partial/noncanonical integrity record");
    *cursor += length; memcpy(value, *cursor, 64); value[64] = '\0'; *cursor += 64;
    if (!digest(value) || *(*cursor)++ != '\n') fail("invalid integrity digest");
}
int main(int argc, char **argv) {
    if (!getuid() || getuid() != geteuid()) fail("requires an unprivileged user"); umask(077);
    bool create = argc == 10 && !strcmp(argv[1], "record"), verify = argc == 5 && !strcmp(argv[1], "verify");
    if (!create && !verify) fail("usage: integrity record ROOT UUID APP SOURCE NAME ID CONFIG ICON | verify ROOT APP CONFIG");
    const char *app_path = create ? argv[4] : argv[3], *binding = create ? argv[8] : argv[4];
    if (!digest(binding) || (create && (!uuid(argv[3]) || (strcmp(argv[9], "0") && strcmp(argv[9], "1"))))) fail("invalid UUID/config/icon arguments");
    int records = root(argv[2], false, true), app = root(app_path, false, false); char id[37]; marker(app, id);
    if (create) {
        if (strcmp(id, argv[3])) fail("build marker UUID mismatch");
        int source = root(argv[5], true, false); bool icon = !strcmp(argv[9], "1");
        struct stat unused;
        if (!fstatat(source, MARKER, &unused, AT_SYMLINK_NOFOLLOW) || errno != ENOENT) fail("source contains a reserved build marker");
        if (!fstatat(source, "Contents/MacOS/launcher", &unused, AT_SYMLINK_NOFOLLOW) || errno != ENOENT) fail("source contains a reserved launcher");
        planned_metadata(source, app, argv[6], argv[7], icon);
        struct hashes original = tree(source, argv[5], true, icon), generated = tree(app, app_path, false, icon);
        if (memcmp(original.unchanged, generated.unchanged, 32)) fail("app resources differ beyond planned files");
        record_create(records, id, binding, original, generated); printf("RECORDED %s\n", id); return 0;
    }
    int directory = openat(records, id, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC); if (directory < 0) syserr("missing integrity record; rebuild required");
    struct stat s = info(directory); if (s.st_uid != getuid() || (s.st_mode & 07777) != 0700) fail("unsafe record directory"); acl_check(directory);
    char buffer[400]; size_t length = read_small(directory, "record.txt", buffer, sizeof(buffer) - 1);
    if (length < 16 || memcmp(buffer, "MCD_INTEGRITY 1\n", 16)) fail("invalid integrity record header");
    const char *cursor = buffer + 16, *end = buffer + length; char recorded[65], source[65], fixed[65], expected[65];
    field(&cursor, end, "config ", recorded); field(&cursor, end, "source ", source); field(&cursor, end, "unchanged ", fixed); field(&cursor, end, "bundle ", expected);
    if (cursor != end || strcmp(recorded, binding)) fail("extra bytes or different instance/config binding");
    struct hashes observed = tree(app, app_path, false, false); char current[65]; hex(observed.full, current);
    if (strcmp(current, expected)) fail("bundle content/structure/mode drift; local re-signing does not repair the build record");
    printf("VERIFIED %s (local content record; not an authenticated trust boundary)\n", id); return 0;
}
