"""Build original pilot authoring material, not a released executable skill pack.

External publishers are linked only. Reference programs and statements below are
original drafts. Regeneration never sets reviewed calibration or invents runtime pins.
"""

import argparse
import json
import random
from pathlib import Path

from socrat.learning.pilot import PilotDraft

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "contracts/content/m7-arrays-pilot-draft.json"
LANGUAGES = ("python", "cpp", "java")
TRACKS = ("foundations", "interview", "competitive")
TUF = "https://takeuforward.org/prep-hub/strivers-a2z-dsa-sheet"
NEETCODE = "https://neetcode.io/roadmap/"
ACCESS = "Plain text, zero-based indices, explicit input/output; no color or diagram required."
PROVENANCE = dict(
    author="Socrat pilot draft assisted by Codex; independent reviewer pending",
    source="Original statements, examples and reference programs authored in this repository",
    license="Project rights review pending; no external exercise text or solutions imported",
    rights_reference="pending original-content rights/editorial review",
    attribution="External curriculum links are optional reading, not sources of copied tasks",
)
FAMILY = {
    "total": "scan_sum",
    "alternating_total": "scan_sum",
    "positive_count": "predicate_count",
    "adjacent_jump": "adjacent_comparison",
    "sign_changes": "adjacent_comparison",
    "first_descent": "adjacent_comparison",
    "minimum_index": "scan_extremum",
    "positive_streak": "run_length",
    "first_target": "target_scan",
    "last_target": "target_scan",
    "target_count": "target_scan",
    "distinct_count": "value_membership",
    "equal_pairs": "multiplicity_pairs",
    "first_unique": "global_count_then_order",
    "prefix_totals": "prefix_materialization",
    "prefix_target": "prefix_search",
    "balanced_cut": "partition_balance",
    "sorted_pair": "ordered_pair_elimination",
    "palindrome": "symmetric_compare",
    "sorted_unique": "read_write_compaction",
    "window_max": "rolling_sum",
    "window_zero": "rolling_sum",
    "window_changes": "rolling_edge_count",
    "nearest_target": "nearest_value_search",
}

# id, title, instruction, example, recognition, correctness, complexity,
# retrieval (prompt, answer), exit (prompt, answer).
TOPICS = [
    (
        "sequence_iteration",
        "Array scans and accumulators",
        "Read the integer count before the values. Visit indices 0 through n-1 once. Choose an initial accumulator that matches the operation: zero for a sum or count; the first value for a minimum of a nonempty array. State what the accumulator means after each visited prefix. Handle n=0 explicitly when permitted.",
        "For [4, -2, 7], a running sum starts at 0 and becomes 4, 2, 9. After index 1, exactly the first two values have contributed.",
        "Use a scan when the answer can be updated from the current value and a small amount of earlier state.",
        "Before index i, the accumulator describes exactly a[0:i]. The update incorporates a[i]; after the last update it describes the entire array.",
        "One constant-time update per value gives O(n) time and O(1) auxiliary space, excluding input and output storage.",
        ("Trace the running sum after visiting the first two values of [4, -2, 7].", "2"),
        ("Trace the number of strictly positive values in [0, -3, 5, 2].", "2"),
    ),
    (
        "linear_search",
        "Search with explicit absence and position",
        "Scan for a target using equality. For the first match, return immediately; for the last match, keep replacing the saved index. Use -1 for absence and keep indices zero-based. Repeated targets make first, last and count different questions. A nearest-value search instead tracks the smallest distance seen; update only for a strictly better distance to preserve the first position in a tie.",
        "In [6, 2, 6], target 6 first appears at index 0, last appears at index 2, and appears twice. Target 9 is absent.",
        "Use a linear scan when no ordering or searchable index has been promised.",
        "All positions before the current index have been examined. A first match cannot have an earlier unexamined match; a saved last match is replaced only by a later equal value.",
        "Worst-case O(n) time, O(1) auxiliary space. An early return improves some inputs without changing the worst case.",
        ("Give the first zero-based index of 6 in [6, 2, 6].", "0"),
        ("Give the last zero-based index of 9 in [6, 2, 6], using -1 for absence.", "-1"),
    ),
    (
        "frequency_counting",
        "Frequencies preserve multiplicity",
        "Map each distinct integer to its occurrence count. A set answers membership, while a frequency map also records repeats. To count equal-value index pairs, each new occurrence pairs with all earlier occurrences of that value. For the first unique value, count first and then scan the original order.",
        "For [8, 8, -1, 8], frequencies are 8:3 and -1:1. The three occurrences of 8 yield three distinct index pairs; the first unique value has index 2.",
        "Use keyed counts when repeated values and their multiplicities affect the answer.",
        "After each update, each stored count equals occurrences of its key in the visited prefix. Every equal pair is counted exactly when its later endpoint is visited.",
        "With hash maps, expected O(n) time and O(d) auxiliary space for d distinct values; hash operations do not promise worst-case constant time.",
        ("How many distinct values occur in [8, 8, -1, 8]?", "2"),
        ("How many index pairs i<j have equal values in [8, 8, -1, 8]?", "3"),
    ),
    (
        "prefix_sums",
        "Prefix sums and boundaries",
        "Define prefix[0]=0 and prefix[i+1]=prefix[i]+a[i]. Then the sum of the half-open range [l,r) is prefix[r]-prefix[l]. Negative values are allowed, so a running sum need not increase. Always decide whether a queried prefix must be nonempty.",
        "For [3, -5, 4], the prefix array is [0, 3, -2, 2]. The sum of [1,3) is prefix[3]-prefix[1]=2-3=-1.",
        "Use prefix sums for repeated additive range queries or to compare left and right totals.",
        "Induction on i establishes that prefix[i] equals the sum of exactly the first i elements. Subtraction removes the shared initial prefix.",
        "O(n) preprocessing and storage; each range-sum query is O(1). A running-prefix search can use O(1) auxiliary space.",
        ("Give the sum of the first two values of [3, -5, 4].", "-2"),
        ("Give the sum of the half-open range [1,3) in [3, -5, 4].", "-1"),
    ),
    (
        "two_pointers",
        "Two pointers with a reason to move",
        "Two pointers must have distinct roles. In a sorted pair-sum search, use the leftmost and rightmost remaining values, moving left forward when the sum is too small and right backward when too large. In a palindrome check, compare symmetric positions. In sorted deduplication, a read pointer scans input and a write pointer bounds the unique output.",
        "Sorted [1, 3, 5, 9] with target 8: 1+9 is too large, then 1+5 too small, then 3+5 matches. These moves rely on sorted order.",
        "Use opposing pointers with an ordering argument, or read/write pointers when retaining a stable compacted subsequence.",
        "For sorted pair search, when a[left]+a[right] is too small, no remaining partner for a[left] can work; the symmetric argument discards a[right] when too large. Pointer movement must not discard an eligible pair.",
        "Each pointer moves at most n times, so O(n) time. Pair/palindrome checks use O(1) auxiliary space; returned deduplicated output may occupy O(n). Sorting would add cost and is not included when sorted input is promised.",
        (
            "Sorted [1, 3, 5, 9], target 8: after the first comparison, give the new right index.",
            "2",
        ),
        ("Give 1 if the integer array [2, 7, 2] is a palindrome, otherwise 0.", "1"),
    ),
    (
        "fixed_window",
        "Fixed-size windows and outgoing values",
        "For a window of k values, calculate the first aggregate once. Moving one position removes the outgoing contribution and adds the incoming contribution. Visit exactly n-k+1 windows. Initialize a maximum from the first window, not zero, because all sums can be negative. This fixed-window rule does not justify a variable-size sum search with negative values.",
        "For [4, -2, 7, 1] and k=2, window sums are 2, 5, 8. Move from 2 to 5 by subtracting 4 and adding 7.",
        "Use a fixed window when the size is specified and the aggregate supports removal and insertion.",
        "After each move the saved sum equals exactly the current k elements, since one departing value is subtracted and the new value is added. Every legal start is processed once.",
        "O(n) time and O(1) auxiliary state for sum/count aggregates. Per-window output occupies O(n-k+1).",
        ("How many size-2 windows exist in an array of length 4?", "3"),
        ("Give the maximum size-2 window sum in [-4, -2, -7].", "-6"),
    ),
]

# Original task bodies return a list of integers in all languages. A shared, explicit
# whitespace interface avoids accidental differences in Java/C++ integer handling.
# key, concept, title, requirement, Python body, C++ body, Java body.
TASKS = [
    (
        "total",
        "sequence_iteration",
        "Total sensor change",
        "Output the sum of all values; an empty array sums to 0.",
        "return [sum(a)]",
        "long long s=0; for(auto x:a) s+=x; return {s};",
        "long s=0; for(long x:a) s+=x; return new long[]{s};",
    ),
    (
        "positive_count",
        "sequence_iteration",
        "Count positive readings",
        "Output the number of values strictly greater than zero.",
        "return [sum(x > 0 for x in a)]",
        "long long s=0; for(auto x:a) s+=x>0; return {s};",
        "long s=0; for(long x:a) if(x>0) s++; return new long[]{s};",
    ),
    (
        "alternating_total",
        "sequence_iteration",
        "Alternating ledger",
        "Output a[0]-a[1]+a[2]-a[3]+...; an empty array yields 0.",
        "return [sum(x if i % 2 == 0 else -x for i, x in enumerate(a))]",
        "long long s=0; for(size_t i=0;i<a.size();i++) s+=(i%2==0?a[i]:-a[i]); return {s};",
        "long s=0; for(int i=0;i<a.length;i++) s+=(i%2==0?a[i]:-a[i]); return new long[]{s};",
    ),
    (
        "adjacent_jump",
        "sequence_iteration",
        "Largest neighboring change",
        "Output the largest absolute difference between neighboring values, or 0 with fewer than two values.",
        "return [max((abs(a[i]-a[i-1]) for i in range(1, len(a))), default=0)]",
        "long long s=0; for(size_t i=1;i<a.size();i++) s=max(s,llabs(a[i]-a[i-1])); return {s};",
        "long s=0; for(int i=1;i<a.length;i++) s=Math.max(s,Math.abs(a[i]-a[i-1])); return new long[]{s};",
    ),
    (
        "sign_changes",
        "sequence_iteration",
        "Adjacent sign switches",
        "Count neighboring pairs where one value is strictly positive and the other strictly negative. A zero breaks a sign switch.",
        "return [sum((a[i]>0 and a[i-1]<0) or (a[i]<0 and a[i-1]>0) for i in range(1,len(a)))]",
        "long long s=0; for(size_t i=1;i<a.size();i++) s+=(a[i]>0&&a[i-1]<0)||(a[i]<0&&a[i-1]>0); return {s};",
        "long s=0; for(int i=1;i<a.length;i++) if((a[i]>0&&a[i-1]<0)||(a[i]<0&&a[i-1]>0)) s++; return new long[]{s};",
    ),
    (
        "minimum_index",
        "sequence_iteration",
        "First minimum location",
        "Output the zero-based index of the first smallest value, or -1 for an empty array.",
        "if not a: return [-1]\nbest=0\nfor i in range(1,len(a)):\n    if a[i]<a[best]: best=i\nreturn [best]",
        "if(a.empty()) return {-1}; size_t b=0; for(size_t i=1;i<a.size();i++) if(a[i]<a[b]) b=i; return {(long long)b};",
        "if(a.length==0) return new long[]{-1}; int b=0; for(int i=1;i<a.length;i++) if(a[i]<a[b]) b=i; return new long[]{b};",
    ),
    (
        "first_descent",
        "sequence_iteration",
        "First order break",
        "Output the first index i>=1 for which a[i]<a[i-1], or -1 if none exists.",
        "return [next((i for i in range(1,len(a)) if a[i]<a[i-1]), -1)]",
        "for(size_t i=1;i<a.size();i++) if(a[i]<a[i-1]) return {(long long)i}; return {-1};",
        "for(int i=1;i<a.length;i++) if(a[i]<a[i-1]) return new long[]{i}; return new long[]{-1};",
    ),
    (
        "positive_streak",
        "sequence_iteration",
        "Longest positive streak",
        "Output the length of the longest consecutive run of strictly positive values, or 0 if none exists.",
        "best=run=0\nfor x in a:\n    run=run+1 if x>0 else 0\n    best=max(best,run)\nreturn [best]",
        "long long b=0,r=0; for(auto x:a){r=x>0?r+1:0; b=max(b,r);} return {b};",
        "long b=0,r=0; for(long x:a){r=x>0?r+1:0; b=Math.max(b,r);} return new long[]{b};",
    ),
    (
        "first_target",
        "linear_search",
        "First matching reading",
        "Output the first index with value p, or -1 if absent.",
        "return [next((i for i,x in enumerate(a) if x==p), -1)]",
        "for(size_t i=0;i<a.size();i++) if(a[i]==p) return {(long long)i}; return {-1};",
        "for(int i=0;i<a.length;i++) if(a[i]==p) return new long[]{i}; return new long[]{-1};",
    ),
    (
        "last_target",
        "linear_search",
        "Last matching reading",
        "Output the last index with value p, or -1 if absent.",
        "last=-1\nfor i,x in enumerate(a):\n    if x==p: last=i\nreturn [last]",
        "long long b=-1; for(size_t i=0;i<a.size();i++) if(a[i]==p) b=i; return {b};",
        "long b=-1; for(int i=0;i<a.length;i++) if(a[i]==p) b=i; return new long[]{b};",
    ),
    (
        "target_count",
        "linear_search",
        "Matching reading count",
        "Output the number of occurrences of p.",
        "return [sum(x==p for x in a)]",
        "long long s=0; for(auto x:a) s+=x==p; return {s};",
        "long s=0; for(long x:a) if(x==p) s++; return new long[]{s};",
    ),
    (
        "nearest_target",
        "linear_search",
        "Nearest target reading",
        "Output the first index minimizing abs(a[i]-p), or -1 for an empty array. Ties choose the smallest index.",
        "if not a: return [-1]\nbest=0\nfor i in range(1,len(a)):\n    if abs(a[i]-p)<abs(a[best]-p): best=i\nreturn [best]",
        "if(a.empty())return {-1};size_t b=0;for(size_t i=1;i<a.size();i++)if(llabs(a[i]-p)<llabs(a[b]-p))b=i;return {(long long)b};",
        "if(a.length==0)return new long[]{-1};int b=0;for(int i=1;i<a.length;i++)if(Math.abs(a[i]-p)<Math.abs(a[b]-p))b=i;return new long[]{b};",
    ),
    (
        "distinct_count",
        "frequency_counting",
        "Distinct channel count",
        "Output the number of distinct integer values.",
        "return [len(set(a))]",
        "unordered_set<long long> s(a.begin(),a.end()); return {(long long)s.size()};",
        "Set<Long> s=new HashSet<>(); for(long x:a) s.add(x); return new long[]{s.size()};",
    ),
    (
        "equal_pairs",
        "frequency_counting",
        "Equal reading pairs",
        "Output the number of index pairs i<j with a[i]=a[j]. Count pairs, not distinct repeated values.",
        "counts={}\ntotal=0\nfor x in a:\n    total+=counts.get(x,0)\n    counts[x]=counts.get(x,0)+1\nreturn [total]",
        "unordered_map<long long,long long> f; long long s=0; for(auto x:a){s+=f[x]; f[x]++;} return {s};",
        "Map<Long,Long> f=new HashMap<>(); long s=0; for(long x:a){long c=f.getOrDefault(x,0L); s+=c; f.put(x,c+1);} return new long[]{s};",
    ),
    (
        "first_unique",
        "frequency_counting",
        "First unpaired channel",
        "Output the first index whose value occurs exactly once in the entire array, or -1 if none exists.",
        "counts={}\nfor x in a: counts[x]=counts.get(x,0)+1\nreturn [next((i for i,x in enumerate(a) if counts[x]==1), -1)]",
        "unordered_map<long long,long long> f; for(auto x:a) f[x]++; for(size_t i=0;i<a.size();i++) if(f[a[i]]==1) return {(long long)i}; return {-1};",
        "Map<Long,Long> f=new HashMap<>(); for(long x:a) f.put(x,f.getOrDefault(x,0L)+1); for(int i=0;i<a.length;i++) if(f.get(a[i])==1) return new long[]{i}; return new long[]{-1};",
    ),
    (
        "prefix_totals",
        "prefix_sums",
        "Ledger prefix totals",
        "Output n integers: the sums of the first 1, 2, ..., n values, in that order. For n=0 output an empty line.",
        "out=[]\ns=0\nfor x in a:\n    s+=x\n    out.append(s)\nreturn out",
        "vector<long long> out; long long s=0; for(auto x:a){s+=x; out.push_back(s);} return out;",
        "long[] out=new long[a.length]; long s=0; for(int i=0;i<a.length;i++){s+=a[i]; out[i]=s;} return out;",
    ),
    (
        "prefix_target",
        "prefix_sums",
        "First target prefix length",
        "Output the smallest nonempty prefix length whose sum is p, or -1 if none exists. Output a length, not an index.",
        "s=0\nfor i,x in enumerate(a):\n    s+=x\n    if s==p: return [i+1]\nreturn [-1]",
        "long long s=0; for(size_t i=0;i<a.size();i++){s+=a[i]; if(s==p) return {(long long)i+1};} return {-1};",
        "long s=0; for(int i=0;i<a.length;i++){s+=a[i]; if(s==p) return new long[]{i+1};} return new long[]{-1};",
    ),
    (
        "balanced_cut",
        "prefix_sums",
        "Balanced ledger cut",
        "Output the smallest cut length c, 0<=c<=n, such that the first c values sum to the remaining n-c values, or -1. Empty sides are permitted.",
        "total=sum(a)\nleft=0\nfor c in range(len(a)+1):\n    if left==total-left: return [c]\n    if c<len(a): left+=a[c]\nreturn [-1]",
        "long long t=0,l=0; for(auto x:a)t+=x; for(size_t c=0;c<=a.size();c++){if(l==t-l)return {(long long)c}; if(c<a.size())l+=a[c];} return {-1};",
        "long t=0,l=0; for(long x:a)t+=x; for(int c=0;c<=a.length;c++){if(l==t-l)return new long[]{c}; if(c<a.length)l+=a[c];} return new long[]{-1};",
    ),
    (
        "sorted_pair",
        "two_pointers",
        "Pair of distinct sorted positions",
        "Input values are nondecreasing. Output 1 if two distinct indices have values summing to p, otherwise 0. A value cannot pair with itself at one index.",
        "l=0\nr=len(a)-1\nwhile l<r:\n    s=a[l]+a[r]\n    if s==p: return [1]\n    if s<p: l+=1\n    else: r-=1\nreturn [0]",
        "int l=0,r=(int)a.size()-1; while(l<r){long long s=a[l]+a[r]; if(s==p)return {1}; if(s<p)l++; else r--;} return {0};",
        "int l=0,r=a.length-1; while(l<r){long s=a[l]+a[r]; if(s==p)return new long[]{1}; if(s<p)l++; else r--;} return new long[]{0};",
    ),
    (
        "palindrome",
        "two_pointers",
        "Symmetric reading sequence",
        "Output 1 if values read identically forwards and backwards, otherwise 0. Empty and one-value arrays are palindromes.",
        "l=0\nr=len(a)-1\nwhile l<r:\n    if a[l]!=a[r]: return [0]\n    l+=1\n    r-=1\nreturn [1]",
        "int l=0,r=(int)a.size()-1; while(l<r){if(a[l]!=a[r])return {0}; l++;r--;} return {1};",
        "int l=0,r=a.length-1; while(l<r){if(a[l]!=a[r])return new long[]{0}; l++;r--;} return new long[]{1};",
    ),
    (
        "sorted_unique",
        "two_pointers",
        "Compact sorted readings",
        "Input values are nondecreasing. Output each distinct value once in sorted order. Use read/write pointers with in-place compaction; for n=0 output an empty line.",
        "w=0\nfor r in range(len(a)):\n    if w==0 or a[r]!=a[w-1]:\n        a[w]=a[r]\n        w+=1\nreturn a[:w]",
        "size_t w=0; for(size_t r=0;r<a.size();r++)if(w==0||a[r]!=a[w-1])a[w++]=a[r]; a.resize(w); return a;",
        "int w=0; for(int r=0;r<a.length;r++)if(w==0||a[r]!=a[w-1])a[w++]=a[r]; return Arrays.copyOf(a,w);",
    ),
    (
        "window_max",
        "fixed_window",
        "Largest fixed-span total",
        "Here p is the window size k with 1<=k<=n. Output the largest sum of any k consecutive values. All-negative arrays are valid.",
        "k=p\ns=sum(a[:k])\nbest=s\nfor i in range(k,len(a)):\n    s+=a[i]-a[i-k]\n    best=max(best,s)\nreturn [best]",
        "size_t k=(size_t)p; long long s=0; for(size_t i=0;i<k;i++)s+=a[i]; long long b=s; for(size_t i=k;i<a.size();i++){s+=a[i]-a[i-k];b=max(b,s);}return {b};",
        "int k=(int)p;long s=0;for(int i=0;i<k;i++)s+=a[i];long b=s;for(int i=k;i<a.length;i++){s+=a[i]-a[i-k];b=Math.max(b,s);}return new long[]{b};",
    ),
    (
        "window_zero",
        "fixed_window",
        "Count zero-total spans",
        "Here p is the window size k with 1<=k<=n. Output the number of k-value windows whose sum is zero, including overlapping windows.",
        "k=p\ns=sum(a[:k])\ncount=int(s==0)\nfor i in range(k,len(a)):\n    s+=a[i]-a[i-k]\n    count+=s==0\nreturn [count]",
        "size_t k=p;long long s=0;for(size_t i=0;i<k;i++)s+=a[i];long long c=s==0;for(size_t i=k;i<a.size();i++){s+=a[i]-a[i-k];c+=s==0;}return {c};",
        "int k=(int)p;long s=0;for(int i=0;i<k;i++)s+=a[i];long c=s==0?1:0;for(int i=k;i<a.length;i++){s+=a[i]-a[i-k];if(s==0)c++;}return new long[]{c};",
    ),
    (
        "window_changes",
        "fixed_window",
        "Changes inside each span",
        "Here p is the window size k with 1<=k<=n. For each k-value window, output its number of adjacent unequal pairs. For k=1 each answer is zero.",
        "k=p\nc=sum(a[i]!=a[i-1] for i in range(1,k))\nout=[c]\nfor end in range(k,len(a)):\n    c-=a[end-k+1]!=a[end-k]\n    c+=a[end]!=a[end-1]\n    out.append(c)\nreturn out",
        "size_t k=p;long long c=0;for(size_t i=1;i<k;i++)c+=a[i]!=a[i-1];vector<long long> out{c};for(size_t e=k;e<a.size();e++){c-=a[e-k+1]!=a[e-k];c+=a[e]!=a[e-1];out.push_back(c);}return out;",
        "int k=(int)p;long c=0;for(int i=1;i<k;i++)if(a[i]!=a[i-1])c++;long[] out=new long[a.length-k+1];out[0]=c;for(int e=k;e<a.length;e++){if(a[e-k+1]!=a[e-k])c--;if(a[e]!=a[e-1])c++;out[e-k+1]=c;}return out;",
    ),
]


def oracle(key, a, p):
    """Small exhaustive definitions independent of optimized reference programs."""
    n = len(a)
    if key == "total":
        return [sum(a)]
    if key == "positive_count":
        return [len([x for x in a if x > 0])]
    if key == "alternating_total":
        return [sum(a[::2]) - sum(a[1::2])]
    if key == "adjacent_jump":
        return [max([0] + [abs(y - x) for x, y in zip(a, a[1:], strict=False)])]
    if key == "sign_changes":
        return [len([1 for x, y in zip(a, a[1:], strict=False) if x * y < 0])]
    if key == "minimum_index":
        return [a.index(min(a)) if a else -1]
    if key == "first_descent":
        matches = [i for i in range(1, n) if a[i] < a[i - 1]]
        return [min(matches) if matches else -1]
    if key == "positive_streak":
        return [
            max(
                [0]
                + [
                    right - left
                    for left in range(n)
                    for right in range(left + 1, n + 1)
                    if all(x > 0 for x in a[left:right])
                ]
            )
        ]
    if key in {"first_target", "last_target", "target_count"}:
        matches = [i for i, x in enumerate(a) if x == p]
        if key == "target_count":
            return [len(matches)]
        return [(min(matches) if key == "first_target" else max(matches)) if matches else -1]
    if key == "distinct_count":
        return [len([i for i, x in enumerate(a) if x not in a[:i]])]
    if key == "equal_pairs":
        return [len([1 for i in range(n) for j in range(i + 1, n) if a[i] == a[j]])]
    if key == "first_unique":
        matches = [i for i, x in enumerate(a) if a.count(x) == 1]
        return [min(matches) if matches else -1]
    if key == "nearest_target":
        candidates = [(abs(x - p), index) for index, x in enumerate(a)]
        return [min(candidates)[1] if candidates else -1]
    if key == "prefix_totals":
        return [sum(a[:i]) for i in range(1, n + 1)]
    if key == "prefix_target":
        matches = [i for i in range(1, n + 1) if sum(a[:i]) == p]
        return [min(matches) if matches else -1]
    if key == "balanced_cut":
        matches = [c for c in range(n + 1) if sum(a[:c]) == sum(a[c:])]
        return [min(matches) if matches else -1]
    if key == "sorted_pair":
        return [int(any(a[i] + a[j] == p for i in range(n) for j in range(i + 1, n)))]
    if key == "palindrome":
        return [int(a == list(reversed(a)))]
    if key == "sorted_unique":
        return sorted(set(a))
    windows = [a[i : i + p] for i in range(n - p + 1)]
    if key == "window_max":
        return [max(sum(w) for w in windows)]
    if key == "window_zero":
        return [len([w for w in windows if sum(w) == 0])]
    if key == "window_changes":
        return [len([1 for x, y in zip(w, w[1:], strict=False) if x != y]) for w in windows]
    raise ValueError(key)


def cases(key, topic):
    rng = random.Random(7007)
    arrays = [
        [],
        [0],
        [7],
        [-4, -2, -7],
        [5, 5, 5],
        [1, -1, 0, 1],
        [2, 7, 2],
        [1, 3, 5, 9],
        [10**9] * 100,
        [-(10**9)] * 100,
        [0] * 100,
        [3, -5, 4],
        [1, 2, 2, -1, 3, 3],
        [-1, 0, 1, 0, -1],
    ]
    arrays += [[rng.randint(-5, 5) for _ in range(rng.randint(0, 20))] for _ in range(20)]
    records = []
    for index, original in enumerate(arrays):
        a = sorted(original) if key in {"sorted_pair", "sorted_unique"} else original
        if topic == "fixed_window":
            if not a:
                continue
            parameters = sorted({1, len(a), max(1, len(a) // 2)})
        elif key in {
            "first_target",
            "last_target",
            "target_count",
            "nearest_target",
            "prefix_target",
            "sorted_pair",
        }:
            parameters = sorted({0, 7, -7, sum(a[:2]), a[0] if a else 0})
        else:
            parameters = [0]
        for p in parameters:
            records.append(
                dict(
                    input=f"{len(a)} {p}\n" + " ".join(map(str, a)) + "\n",
                    expected=" ".join(map(str, oracle(key, a, p))) + "\n",
                    visibility="public" if index < 2 else "hidden",
                )
            )
    # Every fixed-window exercise needs two nonempty public examples.
    if topic == "fixed_window":
        records[0]["visibility"] = "public"
        records[1]["visibility"] = "public"
    return records


def program(language, body):
    if language == "python":
        indented = "\n".join("    " + line for line in body.splitlines())
        return (
            "import sys\n\ndef solve(a, p):\n"
            + indented
            + "\n\ndata=list(map(int,sys.stdin.buffer.read().split()))\nn,p=data[:2]\na=data[2:]\nassert len(a)==n\nprint(' '.join(map(str,solve(a,p))))\n"
        )
    if language == "cpp":
        return (
            "#include <iostream>\n#include <vector>\n#include <algorithm>\n#include <unordered_map>\n#include <unordered_set>\n#include <cstdlib>\nusing namespace std;\nvector<long long> solve(vector<long long> a,long long p){\n"
            + body
            + "\n}\nint main(){int n;long long p;if(!(cin>>n>>p))return 0;vector<long long>a(n);for(auto&x:a)cin>>x;auto out=solve(a,p);for(size_t i=0;i<out.size();i++){if(i)cout<<' ';cout<<out[i];}cout<<'\\n';return 0;}\n"
        )
    return (
        "import java.util.*;\npublic class Main {\nstatic long[] solve(long[] a,long p){\n"
        + body
        + '\n}\npublic static void main(String[]args){Scanner in=new Scanner(System.in);int n=in.nextInt();long p=in.nextLong();long[] a=new long[n];for(int i=0;i<n;i++)a[i]=in.nextLong();long[] out=solve(a,p);StringJoiner s=new StringJoiner(" ");for(long x:out)s.add(Long.toString(x));System.out.println(s);}\n}\n'
    )


def build():
    notes = dict(
        python="Use zero-based list indices and range(n). Python integers handle these sums. Avoid a mutable default argument; negative indices access from the end and are not an absence sentinel.",
        cpp="Use vector<long long> for values and long long for sums. Cast sizes deliberately when using signed pointer indices; unsigned n-1 underflows for an empty vector. Compile as C++20.",
        java="Use long[] and long arithmetic for values and sums. Use int for indices and array lengths. Hash maps require boxed Long keys/values; compare numeric values, not object identity. The entry class is Main, targeting Java 21.",
    )
    resources = [
        dict(
            id="striver_a2z",
            title="Striver A2Z",
            url=TUF,
            role="Primary DSA sequence reference; pilot uses only the early array/hash/pointer topics.",
            access_note="Curriculum access and some practice are free; publisher also offers paid features. Check access at the destination.",
        ),
        dict(
            id="neetcode_roadmap",
            title="NeetCode roadmap",
            url=NEETCODE,
            role="Interview pattern companion for arrays/hashing, two pointers and sliding windows.",
            access_note="Public roadmap; course and individual problem access may differ. No paid subscription is required by this draft.",
        ),
        dict(
            id="cs50_python",
            title="CS50 Python",
            url="https://cs50.harvard.edu/python/",
            role="Optional programming-readiness resource for Python variables, conditions and loops.",
            access_note="Free OpenCourseWare; certificates are separate.",
        ),
        dict(
            id="java_basics",
            title="dev.java language basics",
            url="https://dev.java/learn/language-basics/",
            role="Optional Java readiness reference for variables, arrays and control flow.",
            access_note="Public official learning documentation.",
        ),
        dict(
            id="cpp_basics",
            title="Standard C++ getting-started FAQ",
            url="https://isocpp.org/wiki/faq/newbie",
            role="Optional C++ compiler and language-readiness reference.",
            access_note="Public documentation; automated fetch returned 403, so verify access manually before learner rollout.",
        ),
    ]
    concepts, lessons = [], []
    for (
        key,
        title,
        instruction,
        example,
        recognition,
        correctness,
        complexity,
        retrieval,
        exit_,
    ) in TOPICS:
        concepts.append(
            dict(
                id=key,
                title=title,
                competency=recognition,
                explanation=instruction,
                examples=[example],
                misconceptions=["Boundary conditions and absence must be checked explicitly."],
                evidence_modes=["trace", "implement", "analyze"],
                estimated_minutes=8,
                accessibility=ACCESS,
            )
        )
        for track in TRACKS:
            for language in LANGUAGES:
                prefix = f"{key}_{track}_{language}"
                checks = {}
                for phase, (prompt, answer) in (("retrieval", retrieval), ("exit", exit_)):
                    checks[f"{phase}_check"] = dict(
                        id=f"{prefix}_{phase}",
                        prompt=prompt,
                        response=dict(kind="trace", answer=answer),
                    )
                instruction_track = {
                    "foundations": "Dry-run the example before coding. Write down the state after every step. ",
                    "interview": "Explain the input assumptions and a simple baseline, then justify the chosen pattern before coding. ",
                    "competitive": "Check the constraints and edge cases, estimate complexity, then attempt independently. Timing is low-stakes practice. ",
                }[track]
                lessons.append(
                    dict(
                        id=prefix,
                        track=track,
                        language=language,
                        concept_ids=[key],
                        title=title,
                        instruction=instruction_track + instruction,
                        examples=[example],
                        language_notes=notes[language],
                        pattern_recognition=recognition,
                        correctness=correctness,
                        complexity=complexity,
                        accessibility=ACCESS,
                        source_reference="Original Socrat pilot draft; optional curriculum links in draft.resources",
                        **checks,
                    )
                )
    exercises = []
    for key, topic, title, requirement, py, cpp, java in TASKS:
        interface = "Input: whitespace-separated integers n p, followed by exactly n values. 0<=n<=100 and every value is between -1000000000 and 1000000000. Output space-separated integers on one line. "
        if topic == "fixed_window":
            interface += "For this task n>=1 and 1<=p<=n. "
        elif key in {
            "first_target",
            "last_target",
            "target_count",
            "nearest_target",
            "prefix_target",
            "sorted_pair",
        }:
            interface += "The target p is between -100000000000 and 100000000000. "
        else:
            interface += "p must be 0 and is unused. "
        variants = []
        for language, body in zip(LANGUAGES, (py, cpp, java), strict=True):
            stub = {
                "python": "raise NotImplementedError('Implement solve')",
                "cpp": 'throw "Implement solve";',
                "java": 'throw new UnsupportedOperationException("Implement solve");',
            }[language]
            variants.append(
                dict(
                    language=language,
                    target={"python": "Python 3.12", "cpp": "C++20", "java": "Java 21"}[language],
                    starter_code=program(language, stub),
                    reference_solution=program(language, body),
                )
            )
        exercises.append(
            dict(
                id=key,
                title=title,
                concept_ids=[topic],
                family_id=f"pilot_{FAMILY[key]}",
                statement=interface + requirement,
                rubric="Verify output on empty/singleton inputs where permitted, duplicates, zeros, negative values and wide sums. Explain correctness and complexity separately; passing these small cases does not prove asymptotic complexity or structural novelty.",
                difficulty=1,
                estimated_minutes=8 if topic == "sequence_iteration" else 12,
                variants=variants,
                tests=cases(key, topic),
                provenance=PROVENANCE,
                accessibility=ACCESS,
            )
        )
    prerequisites = [
        ("sequence_iteration", "linear_search"),
        ("sequence_iteration", "frequency_counting"),
        ("sequence_iteration", "prefix_sums"),
        ("linear_search", "two_pointers"),
        ("prefix_sums", "fixed_window"),
    ]
    return PilotDraft.model_validate(
        dict(
            version="m7_pilot_draft_1.0.0",
            status="draft_not_publishable",
            scope="Arrays-and-scans pilot across three tracks and Python/C++/Java; estimated two-week horizon is a rehearsal target, not a calibrated completion promise.",
            resources=[{**x, "checked_on": "2026-10-06"} for x in resources],
            concepts=concepts,
            edges=[
                dict(
                    prerequisite=a,
                    concept=b,
                    minimum_mastery=0.65,
                    rationale="Establish the scan/state prerequisite before this pattern.",
                )
                for a, b in prerequisites
            ],
            lessons=lessons,
            exercises=exercises,
            structural_repairs=[
                dict(
                    exercise_id=source,
                    variant_id=target,
                    structural_change=change,
                    review_reference="pending independent structural review",
                )
                for source, target, change in [
                    (
                        "positive_count",
                        "positive_streak",
                        "Change a global predicate count to consecutive-run state that resets at a nonpositive value.",
                    ),
                    (
                        "first_target",
                        "nearest_target",
                        "Change an equality stop condition to minimum-distance selection with stable tie handling.",
                    ),
                    (
                        "distinct_count",
                        "first_unique",
                        "Change membership accumulation to whole-array multiplicity plus an order-preserving second scan.",
                    ),
                    (
                        "prefix_totals",
                        "balanced_cut",
                        "Change prefix materialization to a split invariant comparing prefix and suffix totals, including empty sides.",
                    ),
                    (
                        "sorted_pair",
                        "sorted_unique",
                        "Change opposing-pointer pair elimination to read/write compaction and unique-prefix maintenance.",
                    ),
                    (
                        "window_max",
                        "window_changes",
                        "Change a rolling value sum to rolling edge indicators; outgoing/incoming edge boundaries differ from value boundaries.",
                    ),
                ]
            ],
            competitive_penalty=dict(
                wrong_submit_seconds=60, review_reference="pending independent pilot policy review"
            ),
            promotion_requirements=[
                "Named independent content, rights, language and structural-family/repair reviews against the exact draft digest",
                "Approved immutable execution runtime references and worker verification; no runtime pins are fabricated in this draft",
                "Separate protected diagnostic/assessment inventory and limited released goal targets; practice checks cannot supply assessment coverage",
                "Candidate duration, difficulty and penalty calibration; actual learner/staff/accessibility/staging records are deferred",
                "Convert reviewed content into a launch SkillPack and pass static and fourteen-day production-planner audits before authenticated publication",
            ],
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Fail if the committed draft differs from regeneration"
    )
    args = parser.parse_args()
    draft = build()
    rendered = json.dumps(draft.model_dump(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit("Pilot draft differs; regenerate and review the diff")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered, encoding="utf-8", newline="\n")
    print(json.dumps(draft.report(), indent=2))


if __name__ == "__main__":
    main()
