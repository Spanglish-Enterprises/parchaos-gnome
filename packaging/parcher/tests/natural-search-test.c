/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Tests for parcher-natural-search.c (ticket #120).
 *
 * Build and run against a Files source tree that has the patch applied:
 *   gcc -I<tree>/src -o t natural-search-test.c $(pkg-config --cflags --libs glib-2.0) && ./t
 */
#include "parcher-natural-search.c"

static int failures;

static void
check (gboolean ok, const char *what, const char *detail)
{
    if (!ok)
    {
        failures++;
        g_print ("FAIL %s %s\n", what, detail ? detail : "");
    }
}

static char *
range_text (GDateTime *from, GDateTime *to)
{
    g_autofree char *a = g_date_time_format (from, "%Y-%m-%d");
    g_autofree char *b = g_date_time_format (to, "%Y-%m-%d");
    return g_strdup_printf ("%s..%s", a, b);
}

static char *
groups_text (GArray *groups)
{
    GString *s = g_string_new (NULL);

    for (guint i = 0; i < groups->len; i++)
    {
        g_string_append_printf (s, "%s%u", i ? "," : "", g_array_index (groups, guint, i));
    }
    return g_string_free (s, FALSE);
}

typedef struct
{
    const char *text;
    const char *range;
    const char *groups;
    const char *words;
    const char *phrase;
} Case;

int
main (void)
{
    /* Wednesday 30 September 2026, 15:30 local time. */
    g_autoptr (GDateTime) now = g_date_time_new_local (2026, 9, 30, 15, 30, 0);
    const char *plain[] = {"firefox", "pdf", "photos", "terminal", "text editor", "last", "week", "ab", "", NULL};
    const Case cases[] = {
        {"pdf from last week", "2026-09-21..2026-09-27", "6", "", "Last week"},
        {"that PDF from last week", "2026-09-21..2026-09-27", "6", "", "Last week"},
        {"spreadsheets from yesterday", "2026-09-29..2026-09-29", "9", "", "Yesterday"},
        {"photos today", "2026-09-30..2026-09-30", "7", "", "Today"},
        {"documents this week", "2026-09-28..2026-09-30", "3,6", "", "This week"},
        {"videos last month", "2026-08-01..2026-08-31", "11", "", "Last month"},
        {"invoice pdf last month", "2026-08-01..2026-08-31", "6", "invoice", "Last month"},
        {"files from the last 7 days", "2026-09-23..2026-09-30", "", "", "Last 7 days"},
        {"images past 2 weeks", "2026-09-16..2026-09-30", "7", "", "Past 2 weeks"},
        {"slides 3 days ago", "2026-09-27..2026-09-27", "8", "", "3 days ago"},
        {"music and podcasts this year", "2026-01-01..2026-09-30", "5", "podcasts", "This year"},
        {"budget this month", "2026-09-01..2026-09-30", "", "budget", "This month"},
        {"last year", "2025-01-01..2025-12-31", "", "", "Last year"},
        {"  Photos   YESTERDAY  ", "2026-09-29..2026-09-29", "7", "", "Yesterday"},
    };

    for (int i = 0; plain[i] != NULL; i++)
    {
        check (!parcher_natural_search_parse (plain[i], now, NULL, NULL, NULL, NULL, NULL), "plain search left alone", plain[i]);
    }

    for (gsize i = 0; i < G_N_ELEMENTS (cases); i++)
    {
        g_autofree char *rest = NULL;
        g_autofree char *phrase = NULL;
        g_autofree char *r = NULL;
        g_autofree char *g = NULL;
        g_autoptr (GArray) groups = NULL;
        g_autoptr (GDateTime) from = NULL;
        g_autoptr (GDateTime) to = NULL;

        if (!parcher_natural_search_parse (cases[i].text, now, &rest, &phrase, &groups, &from, &to))
        {
            check (FALSE, "should parse", cases[i].text);
            continue;
        }
        r = range_text (from, to);
        g = groups_text (groups);
        check (g_str_equal (r, cases[i].range), cases[i].text, r);
        check (g_str_equal (g, cases[i].groups), cases[i].text, g);
        check (g_str_equal (rest, cases[i].words), cases[i].text, rest);
        check (g_str_equal (phrase, cases[i].phrase), cases[i].text, phrase);
    }

    /* Hostile punctuation never becomes a name word. */
    {
        g_autofree char *rest = NULL;
        g_autoptr (GArray) groups = NULL;
        g_autoptr (GDateTime) from = NULL;
        g_autoptr (GDateTime) to = NULL;

        check (parcher_natural_search_parse ("pdf x\") } DELETE { \\ '' from last week", now, &rest, NULL, &groups, &from, &to),
               "hostile text still parses", NULL);
        check (rest != NULL && strpbrk (rest, "\"'\\(){}") == NULL, "no punctuation in the words", rest);
    }

    g_print (failures == 0 ? "natural-search: all checks passed\n" : "natural-search: %d check(s) failed\n", failures);
    return failures == 0 ? 0 : 1;
}
