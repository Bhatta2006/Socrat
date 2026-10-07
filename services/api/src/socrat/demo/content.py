"""Original sample curriculum, generated deterministically; not release-reviewed.

The existing schema's `reviewed` metadata permits deterministic selection. In this
isolated demo pack it means author-checked sample metadata, never editorial release
approval. The seed boundary and visible banner are mandatory.
"""

import random
from copy import deepcopy

from socrat.learning.audit import planning_audit
from socrat.skillpacks.schema import SkillPack

LANGUAGES = ("python", "cpp", "java")
PROVENANCE = dict(
    author="Socrat demo authors",
    source="Original sample curriculum, 2026-10-07",
    license="Project sample content",
    rights_reference="original-demo-2026-10-07",
    attribution="Demo only; not reviewed for release",
)
# id, title, prerequisite, lesson, worked example, retrieval prompt/answer, exit prompt/answer
CONCEPTS = [
    (
        "language_foundations",
        "Language foundations",
        None,
        "A variable names a value. Read integer input, store a running result, and print exactly the requested output. Assignment replaces the stored value; it is not an equality test.",
        "Start total at 0. Read 4, then -1: total becomes 4, then 3. Print 3.",
        "Start at 2 and add 3. What is the new value?",
        "5",
        "Start at 7 and subtract 4. What is the new value?",
        "3",
    ),
    (
        "sequence_iteration",
        "Loops and sequences",
        None,
        "Visit each element exactly once. Before visit i, the accumulator describes the first i elements. Initialize it before the loop and update it once per element.",
        "For [2, 0, 3], a positive counter changes 0 → 1 → 1 → 2.",
        "How many elements does [8, 4, 9] contain?",
        "3",
        "How many positive values are in [2, -1, 0, 5]?",
        "2",
    ),
    (
        "complexity",
        "Time and space complexity",
        "sequence_iteration",
        "Count work as input grows. One complete scan takes O(n) time. A loop that visits all n entries for each of n entries takes O(n²). Extra storage is measured separately.",
        "A 4-element scan makes 4 visits; two full nested scans make 16 visits.",
        "How many visits in one scan of 5 elements?",
        "5",
        "How many pairs in two full nested loops of length 3?",
        "9",
    ),
    (
        "arrays_strings",
        "Arrays and strings",
        "sequence_iteration",
        "An array stores an ordered sequence with indexed access. A string is a sequence of characters. Check empty input, boundaries, and duplicates before choosing an initial value.",
        "In [7, 2, 7], indices are 0, 1, 2. The maximum is 7; reversing gives [7, 2, 7].",
        "What is the last valid index for a sequence of length 4?",
        "3",
        "What is the middle value in [9, 4, 2]?",
        "4",
    ),
    (
        "hash_maps",
        "Hash maps and sets",
        "arrays_strings",
        "A set records membership; a map records a value per key. Scan input and update a frequency map. Hash-based lookup is expected O(1), rather than a new complete scan per query.",
        "For [4, 4, 2], frequencies are {4: 2, 2: 1}. There are two distinct keys.",
        "How many distinct keys occur in [1, 1, 2]?",
        "2",
        "How often does 3 occur in [3, 1, 3, 3]?",
        "3",
    ),
    (
        "two_pointers",
        "Two pointers",
        "arrays_strings",
        "Two indices can shrink a search interval. On a sorted array, if the end values sum too small, advance the left pointer; if too large, retreat the right pointer. State why each discarded candidate cannot work.",
        "For sorted [1, 3, 7, 9] and target 10, endpoints 1 + 9 match; then 3 + 7 match.",
        "For target 10, what sum do endpoints 1 and 9 make?",
        "10",
        "In [1, 3, 7, 9], how many disjoint pairs sum to 10?",
        "2",
    ),
    (
        "sliding_window",
        "Sliding windows",
        "two_pointers",
        "When moving a fixed-width window, remove the departing value and add the arriving value. Maintain a sum that describes exactly the current interval. A single moving scan avoids recomputing each window.",
        "Width two in [2, 5, 1]: first sum 7, next sum 6; maximum 7.",
        "What is the sum of the first width-two window in [3, 4, 2]?",
        "7",
        "What is the largest adjacent-pair sum in [1, 5, 2]?",
        "7",
    ),
    (
        "stack",
        "Stacks",
        "arrays_strings",
        "A stack removes the most recently added element. Push positive events; a zero event pops if the stack is nonempty. The top is the last surviving push, not the largest value.",
        "Events [4, 7, 0] leave [4]. Events [0, 3] leave [3].",
        "After pushing 2 then 5 and popping once, what remains?",
        "2",
        "After events [3, 4, 0], what is the remaining sum?",
        "3",
    ),
    (
        "queue",
        "Queues",
        "arrays_strings",
        "A queue removes the earliest added element. Push at the back and remove from the front. Use a deque or a head index so repeated front removals do not shift an entire array.",
        "Events [4, 7, 0] leave [7], because 4 entered first.",
        "After enqueueing 2 then 5 and removing once, what remains?",
        "5",
        "After events [3, 4, 0], what is the remaining sum?",
        "4",
    ),
    (
        "binary_search",
        "Binary search",
        "two_pointers",
        "Maintain a half-open sorted search interval [lo, hi). Lower-bound search finds the first index whose value is at least a target. Each comparison discards half the interval; empty input returns index 0.",
        "For [-2, -1, 3] and target 0, lower bound is index 2.",
        "What is the first nonnegative index in [-3, 1, 2]?",
        "1",
        "What is the first nonnegative index in [-2, -1, 4]?",
        "2",
    ),
    (
        "recursion",
        "Recursion",
        "language_foundations",
        "A recursive function solves a smaller instance and has a terminating base case. For a sum, the empty prefix returns 0 and a nonempty prefix returns its last value plus the sum of the preceding prefix.",
        "sum([2, 3]) = 3 + sum([2]) = 3 + 2 + sum([]) = 5.",
        "What is the empty-sum base case?",
        "0",
        "What is recursive sum([4, -1])?",
        "3",
    ),
    (
        "linked_lists",
        "Linked lists",
        "recursion",
        "A linked-list node stores a value and a next reference. Traverse by following next. To reverse a chain, preserve next before redirecting it to the previous node; then advance both references.",
        "Build 2 → 5 → null. Reversal produces 5 → 2 → null.",
        "How many nodes are in 2 → 5 → null?",
        "2",
        "What is the new head value when reversing 2 → 5 → 7?",
        "7",
    ),
    (
        "trees",
        "Binary trees",
        "recursion",
        "A binary tree has at most two children per node. In a complete-tree array representation the children of index i are 2i+1 and 2i+2. Height is one plus the larger child height, with empty height zero.",
        "A complete tree with 3 nodes has a root and two children: height 2.",
        "What is the height of a one-node tree?",
        "1",
        "What is the height of a complete tree with 7 nodes?",
        "3",
    ),
    (
        "graph_bfs_dfs",
        "Graphs: BFS and DFS",
        "queue",
        "Vertices and edges describe connections. A visited set prevents repeated exploration of cycles. BFS uses a queue to explore by distance; DFS uses a stack or recursion to explore a branch before backtracking.",
        "Successor edges [1, 2, 2] starting at vertex 0 visit 0, 1, 2 once. The self-loop at 2 adds no new visit.",
        "How many vertices are reached from 0 along 0 → 1 → 2?",
        "3",
        "How many vertices are reached if vertex 0 points to itself?",
        "1",
    ),
]

# All tasks consume n followed by n integers, with n in [0, 30]. Bodies return a scalar.
# Each family changes the computation, not just the labels or sample numbers.
TASKS = [
    (
        "language_foundations",
        "sum",
        "Sum the readings",
        "Print the sum of all readings; the empty sum is 0.",
        "return sum(a)",
        "long long r=0; for(auto x:a) r+=x; return r;",
        "long r=0; for(long x:a) r+=x; return r;",
    ),
    (
        "language_foundations",
        "squares",
        "Energy total",
        "Print the sum of squared readings.",
        "return sum(x*x for x in a)",
        "long long r=0; for(auto x:a) r+=x*x; return r;",
        "long r=0; for(long x:a) r+=x*x; return r;",
    ),
    (
        "language_foundations",
        "absolute",
        "Total movement",
        "Print the sum of absolute readings.",
        "return sum(abs(x) for x in a)",
        "long long r=0; for(auto x:a) r+=abs(x); return r;",
        "long r=0; for(long x:a) r+=Math.abs(x); return r;",
    ),
    (
        "language_foundations",
        "weighted",
        "Position-weighted readings",
        "Multiply each reading by its one-based position and print the sum.",
        "return sum((i+1)*x for i,x in enumerate(a))",
        "long long r=0; for(int i=0;i<(int)a.size();i++) r+=(i+1)*a[i]; return r;",
        "long r=0; for(int i=0;i<a.length;i++) r+=(i+1)*a[i]; return r;",
    ),
    (
        "language_foundations",
        "alternating",
        "Alternating balance",
        "Add readings at even zero-based indices and subtract readings at odd indices.",
        "return sum(x if i%2==0 else -x for i,x in enumerate(a))",
        "long long r=0; for(int i=0;i<(int)a.size();i++) r+=(i%2==0?a[i]:-a[i]); return r;",
        "long r=0; for(int i=0;i<a.length;i++) r+=(i%2==0?a[i]:-a[i]); return r;",
    ),
    (
        "language_foundations",
        "clamped",
        "Positive total",
        "Print the sum of strictly positive readings.",
        "return sum(x for x in a if x>0)",
        "long long r=0; for(auto x:a) if(x>0)r+=x; return r;",
        "long r=0; for(long x:a)if(x>0)r+=x; return r;",
    ),
    (
        "language_foundations",
        "difference",
        "Endpoint change",
        "Print last minus first; print 0 if there are no readings.",
        "return a[-1]-a[0] if a else 0",
        "return a.empty()?0:a.back()-a.front();",
        "return a.length==0?0:a[a.length-1]-a[0];",
    ),
    (
        "language_foundations",
        "adjacent_delta",
        "Total adjacent change",
        "Print the sum of absolute differences between adjacent readings.",
        "return sum(abs(a[i]-a[i-1]) for i in range(1,len(a)))",
        "long long r=0; for(int i=1;i<(int)a.size();i++)r+=abs(a[i]-a[i-1]);return r;",
        "long r=0;for(int i=1;i<a.length;i++)r+=Math.abs(a[i]-a[i-1]);return r;",
    ),
    (
        "sequence_iteration",
        "positive_count",
        "Count positive readings",
        "Print the number of strictly positive readings.",
        "return sum(x>0 for x in a)",
        "long long r=0;for(auto x:a)r+=x>0;return r;",
        "long r=0;for(long x:a)if(x>0)r++;return r;",
    ),
    (
        "sequence_iteration",
        "even_count",
        "Count even readings",
        "Print the number of even readings, including zero.",
        "return sum(x%2==0 for x in a)",
        "long long r=0;for(auto x:a)r+=x%2==0;return r;",
        "long r=0;for(long x:a)if(x%2==0)r++;return r;",
    ),
    (
        "sequence_iteration",
        "negative_count",
        "Count negative readings",
        "Print the number of negative readings.",
        "return sum(x<0 for x in a)",
        "long long r=0;for(auto x:a)r+=x<0;return r;",
        "long r=0;for(long x:a)if(x<0)r++;return r;",
    ),
    (
        "sequence_iteration",
        "zeros",
        "Count idle readings",
        "Print the number of readings equal to zero.",
        "return a.count(0)",
        "return count(a.begin(),a.end(),0);",
        "long r=0;for(long x:a)if(x==0)r++;return r;",
    ),
    (
        "sequence_iteration",
        "rises",
        "Count rises",
        "Print the number of adjacent pairs where the later reading is larger.",
        "return sum(a[i]>a[i-1] for i in range(1,len(a)))",
        "long long r=0;for(int i=1;i<(int)a.size();i++)r+=a[i]>a[i-1];return r;",
        "long r=0;for(int i=1;i<a.length;i++)if(a[i]>a[i-1])r++;return r;",
    ),
    (
        "sequence_iteration",
        "changes",
        "Count changes",
        "Print the number of adjacent pairs with unequal values.",
        "return sum(a[i]!=a[i-1] for i in range(1,len(a)))",
        "long long r=0;for(int i=1;i<(int)a.size();i++)r+=a[i]!=a[i-1];return r;",
        "long r=0;for(int i=1;i<a.length;i++)if(a[i]!=a[i-1])r++;return r;",
    ),
    (
        "sequence_iteration",
        "first_positive",
        "Find the first positive reading",
        "Print its zero-based index, or -1 if no positive reading exists.",
        "return next((i for i,x in enumerate(a) if x>0),-1)",
        "for(int i=0;i<(int)a.size();i++)if(a[i]>0)return i;return -1;",
        "for(int i=0;i<a.length;i++)if(a[i]>0)return i;return -1;",
    ),
    (
        "sequence_iteration",
        "last_zero",
        "Find the last idle reading",
        "Print the last zero's zero-based index, or -1 if there is none.",
        "return next((i for i in range(len(a)-1,-1,-1) if a[i]==0),-1)",
        "for(int i=(int)a.size()-1;i>=0;i--)if(a[i]==0)return i;return -1;",
        "for(int i=a.length-1;i>=0;i--)if(a[i]==0)return i;return -1;",
    ),
    (
        "complexity",
        "single_scan",
        "Count scan visits",
        "A scan visits each element once. Print the visit count.",
        "return len(a)",
        "return a.size();",
        "return a.length;",
    ),
    (
        "complexity",
        "pair_scan",
        "Count nested visits",
        "Two full nested scans visit every ordered pair of positions. Print the visit count.",
        "return len(a)**2",
        "return (long long)a.size()*a.size();",
        "return (long)a.length*a.length;",
    ),
    (
        "arrays_strings",
        "range",
        "Reading range",
        "Print maximum minus minimum, or 0 for empty input.",
        "return max(a)-min(a) if a else 0",
        "return a.empty()?0:*max_element(a.begin(),a.end())-*min_element(a.begin(),a.end());",
        "if(a.length==0)return 0;long lo=a[0],hi=a[0];for(long x:a){lo=Math.min(lo,x);hi=Math.max(hi,x);}return hi-lo;",
    ),
    (
        "arrays_strings",
        "mirror",
        "Mirror distance",
        "Sum absolute differences between mirrored positions, counting each pair once.",
        "return sum(abs(a[i]-a[-1-i]) for i in range(len(a)//2))",
        "long long r=0;for(int i=0;i<(int)a.size()/2;i++)r+=abs(a[i]-a[a.size()-1-i]);return r;",
        "long r=0;for(int i=0;i<a.length/2;i++)r+=Math.abs(a[i]-a[a.length-1-i]);return r;",
    ),
    (
        "hash_maps",
        "distinct",
        "Distinct readings",
        "Print the number of distinct readings.",
        "return len(set(a))",
        "return set<long long>(a.begin(),a.end()).size();",
        "Set<Long>s=new HashSet<>();for(long x:a)s.add(x);return s.size();",
    ),
    (
        "hash_maps",
        "duplicates",
        "Repeated readings",
        "Count readings after the first occurrence of their value.",
        "return len(a)-len(set(a))",
        "return a.size()-set<long long>(a.begin(),a.end()).size();",
        "Set<Long>s=new HashSet<>();for(long x:a)s.add(x);return a.length-s.size();",
    ),
    (
        "two_pointers",
        "target_pairs",
        "Disjoint pairs totaling ten",
        "Sort the readings. Use each reading at most once and print the maximum number of pairs summing to 10.",
        "b=sorted(a);l=0;r=len(b)-1;count=0\nwhile l<r:\n    s=b[l]+b[r]\n    if s==10: count+=1;l+=1;r-=1\n    elif s<10: l+=1\n    else: r-=1\nreturn count",
        "sort(a.begin(),a.end());int l=0,r=(int)a.size()-1;long long k=0;while(l<r){auto s=a[l]+a[r];if(s==10){k++;l++;r--;}else if(s<10)l++;else r--;}return k;",
        "Arrays.sort(a);int l=0,r=a.length-1;long k=0;while(l<r){long s=a[l]+a[r];if(s==10){k++;l++;r--;}else if(s<10)l++;else r--;}return k;",
    ),
    (
        "two_pointers",
        "palindrome",
        "Symmetric readings",
        "Print 1 if mirrored readings all match, otherwise 0. Empty input is symmetric.",
        "return int(a==a[::-1])",
        "for(int l=0,r=(int)a.size()-1;l<r;l++,r--)if(a[l]!=a[r])return 0;return 1;",
        "for(int l=0,r=a.length-1;l<r;l++,r--)if(a[l]!=a[r])return 0;return 1;",
    ),
    (
        "sliding_window",
        "pair_max",
        "Largest adjacent window",
        "Print the largest sum of two adjacent readings, or 0 if fewer than two exist.",
        "return max((a[i]+a[i-1] for i in range(1,len(a))),default=0)",
        "if(a.size()<2)return 0;long long r=a[0]+a[1];for(int i=2;i<(int)a.size();i++)r=max(r,a[i]+a[i-1]);return r;",
        "if(a.length<2)return 0;long r=a[0]+a[1];for(int i=2;i<a.length;i++)r=Math.max(r,a[i]+a[i-1]);return r;",
    ),
    (
        "sliding_window",
        "triple_max",
        "Largest three-reading window",
        "Print the largest sum of three adjacent readings, or 0 if fewer than three exist.",
        "return max((sum(a[i:i+3]) for i in range(len(a)-2)),default=0)",
        "if(a.size()<3)return 0;long long s=a[0]+a[1]+a[2],r=s;for(int i=3;i<(int)a.size();i++){s+=a[i]-a[i-3];r=max(r,s);}return r;",
        "if(a.length<3)return 0;long s=a[0]+a[1]+a[2],r=s;for(int i=3;i<a.length;i++){s+=a[i]-a[i-3];r=Math.max(r,s);}return r;",
    ),
]


def add_structures():
    for concept, fifo in (("stack", False), ("queue", True)):
        for metric in ("sum", "size"):
            py = (
                "s=[]\nfor x in a:\n    if x>0:s.append(x)\n    elif x==0 and s:s.pop("
                + ("0" if fifo else "")
                + ")\nreturn "
                + ("sum(s)" if metric == "sum" else "len(s)")
            )
            cpp = (
                "deque<long long>s;for(auto x:a){if(x>0)s.push_back(x);else if(x==0&&!s.empty())s."
                + ("pop_front" if fifo else "pop_back")
                + "();}"
                + (
                    "long long r=0;for(auto x:s)r+=x;return r;"
                    if metric == "sum"
                    else "return s.size();"
                )
            )
            java = (
                "Deque<Long>s=new ArrayDeque<>();for(long x:a){if(x>0)s.addLast(x);else if(x==0&&!s.isEmpty())s."
                + ("removeFirst" if fifo else "removeLast")
                + "();}"
                + (
                    "long r=0;for(long x:s)r+=x;return r;"
                    if metric == "sum"
                    else "return s.size();"
                )
            )
            TASKS.append(
                (
                    concept,
                    metric,
                    f"{concept.title()} event {metric}",
                    f"Positive values push; zero removes the {'oldest' if fifo else 'newest'} value if present; negative values do nothing. Print the remaining {metric}.",
                    py,
                    cpp,
                    java,
                )
            )
    TASKS.extend(
        [
            (
                "binary_search",
                "lower",
                "First nonnegative position",
                "Sort readings; print the index of the first nonnegative reading, or n if none exists.",
                "import bisect\nreturn bisect.bisect_left(sorted(a),0)",
                "sort(a.begin(),a.end());return lower_bound(a.begin(),a.end(),0)-a.begin();",
                "Arrays.sort(a);int l=0,r=a.length;while(l<r){int m=l+(r-l)/2;if(a[m]<0)l=m+1;else r=m;}return l;",
            ),
            (
                "binary_search",
                "upper",
                "First positive position",
                "Sort readings; print the index of the first positive reading, or n if none exists.",
                "import bisect\nreturn bisect.bisect_right(sorted(a),0)",
                "sort(a.begin(),a.end());return upper_bound(a.begin(),a.end(),0)-a.begin();",
                "Arrays.sort(a);int l=0,r=a.length;while(l<r){int m=l+(r-l)/2;if(a[m]<=0)l=m+1;else r=m;}return l;",
            ),
            (
                "recursion",
                "recursive_sum",
                "Recursive prefix total",
                "Use a base case and a shrinking prefix to compute the sum.",
                "def rec(i):\n    return 0 if i==0 else a[i-1]+rec(i-1)\nreturn rec(len(a))",
                "function<long long(int)>rec=[&](int i){return i==0?0LL:a[i-1]+rec(i-1);};return rec(a.size());",
                "return recSum(a,a.length);",
            ),
            (
                "recursion",
                "recursive_even",
                "Recursive even count",
                "Use a shrinking prefix to count even readings.",
                "def rec(i):\n    return 0 if i==0 else int(a[i-1]%2==0)+rec(i-1)\nreturn rec(len(a))",
                "function<long long(int)>rec=[&](int i){return i==0?0LL:(a[i-1]%2==0)+rec(i-1);};return rec(a.size());",
                "return recEven(a,a.length);",
            ),
            (
                "linked_lists",
                "list_sum",
                "Traverse a node chain",
                "Build one node per reading, traverse next references, and print the sum.",
                "head=None\nfor x in reversed(a):head=(x,head)\nr=0\nwhile head:r+=head[0];head=head[1]\nreturn r",
                "struct Node{long long x;Node*next;};Node*head=nullptr;for(auto it=a.rbegin();it!=a.rend();++it)head=new Node{*it,head};long long r=0;while(head){r+=head->x;Node*t=head;head=head->next;delete t;}return r;",
                "Node head=null;for(int i=a.length-1;i>=0;i--)head=new Node(a[i],head);long r=0;while(head!=null){r+=head.x;head=head.next;}return r;",
            ),
            (
                "linked_lists",
                "reverse_head",
                "Reverse a chain",
                "Build and reverse a node chain, and print its new head value. Print 0 for empty input.",
                "head=None\nfor x in a:head=(x,head)\nreturn head[0] if head else 0",
                "struct Node{long long x;Node*next;};Node*head=nullptr;for(auto x:a)head=new Node{x,head};long long r=head?head->x:0;while(head){Node*t=head;head=head->next;delete t;}return r;",
                "Node head=null;for(long x:a)head=new Node(x,head);return head==null?0:head.x;",
            ),
            (
                "trees",
                "height",
                "Complete-tree height",
                "Readings occupy a complete binary tree in breadth-first order. Print its height, with empty height 0.",
                "def height(i):\n    return 0 if i>=len(a) else 1+max(height(2*i+1),height(2*i+2))\nreturn height(0)",
                "function<long long(int)>h=[&](int i){return i>=(int)a.size()?0LL:1+max(h(2*i+1),h(2*i+2));};return h(0);",
                "return height(a,0);",
            ),
            (
                "trees",
                "leaves",
                "Complete-tree leaves",
                "Print the number of nodes with no children in the complete-tree representation.",
                "return sum(2*i+1>=len(a) for i in range(len(a)))",
                "long long r=0;for(int i=0;i<(int)a.size();i++)r+=2*i+1>=(int)a.size();return r;",
                "long r=0;for(int i=0;i<a.length;i++)if(2*i+1>=a.length)r++;return r;",
            ),
            (
                "graph_bfs_dfs",
                "bfs",
                "Explore successor edges with BFS",
                "Vertex i has a directed edge to a[i] only if that value is a valid vertex index. Print the number of distinct vertices reachable from 0; print 0 for no vertices.",
                "from collections import deque\nq=deque([0] if a else []);seen=set()\nwhile q:\n    v=q.popleft()\n    if v in seen:continue\n    seen.add(v)\n    if 0<=a[v]<len(a):q.append(a[v])\nreturn len(seen)",
                "queue<int>q;if(!a.empty())q.push(0);set<int>s;while(!q.empty()){int v=q.front();q.pop();if(s.count(v))continue;s.insert(v);if(a[v]>=0&&a[v]<(int)a.size())q.push(a[v]);}return s.size();",
                "Queue<Integer>q=new ArrayDeque<>();if(a.length>0)q.add(0);Set<Integer>s=new HashSet<>();while(!q.isEmpty()){int v=q.remove();if(!s.add(v))continue;if(a[v]>=0&&a[v]<a.length)q.add((int)a[v]);}return s.size();",
            ),
            (
                "graph_bfs_dfs",
                "dfs",
                "Explore successor edges with DFS",
                "Use a stack and visited set. Vertex i points to a[i] when it is a valid index. Print the sum of reached vertex indices, starting from vertex 0.",
                "stack=[0] if a else [];seen=set()\nwhile stack:\n    v=stack.pop()\n    if v in seen:continue\n    seen.add(v)\n    if 0<=a[v]<len(a):stack.append(a[v])\nreturn sum(seen)",
                "vector<int>s;if(!a.empty())s.push_back(0);set<int>seen;long long r=0;while(!s.empty()){int v=s.back();s.pop_back();if(seen.count(v))continue;seen.insert(v);r+=v;if(a[v]>=0&&a[v]<(int)a.size())s.push_back(a[v]);}return r;",
                "Deque<Integer>s=new ArrayDeque<>();if(a.length>0)s.push(0);Set<Integer>seen=new HashSet<>();long r=0;while(!s.isEmpty()){int v=s.pop();if(!seen.add(v))continue;r+=v;if(a[v]>=0&&a[v]<a.length)s.push((int)a[v]);}return r;",
            ),
        ]
    )


add_structures()


def source(language: str, body: str | None) -> str:
    if language == "python":
        code = body or "# Write your computation here.\nreturn 0"
        return (
            "def solve(a):\n"
            + "\n".join("    " + line for line in code.splitlines())
            + "\n\nimport sys\ndata=list(map(int,sys.stdin.read().split()))\nn=data[0]\nprint(solve(data[1:1+n]))\n"
        )
    if language == "cpp":
        return (
            "#include <bits/stdc++.h>\nusing namespace std;\nlong long solve(vector<long long> a){\n"
            + (body or "// Write your computation here.\nreturn 0;")
            + "\n}\nint main(){int n;cin>>n;vector<long long>a(n);for(auto &x:a)cin>>x;cout<<solve(a)<<'\\n';}\n"
        )
    return (
        "import java.util.*;\npublic class Solution {\nstatic class Node {long x;Node next;Node(long v,Node n){x=v;next=n;}}\nstatic long recSum(long[] a,int i){return i==0?0:a[i-1]+recSum(a,i-1);}\nstatic long recEven(long[] a,int i){return i==0?0:(a[i-1]%2==0?1:0)+recEven(a,i-1);}\nstatic long height(long[] a,int i){return i>=a.length?0:1+Math.max(height(a,2*i+1),height(a,2*i+2));}\nstatic long solve(long[] a){\n"
        + (body or "// Write your computation here.\nreturn 0;")
        + "\n}\npublic static void main(String[]args){Scanner s=new Scanner(System.in);int n=s.nextInt();long[]a=new long[n];for(int i=0;i<n;i++)a[i]=s.nextLong();System.out.println(solve(a));}\n}\n"
    )


def task_tests(body: str) -> list[dict]:
    scope: dict = {}
    exec("def oracle(a):\n" + "\n".join("    " + line for line in body.splitlines()), scope)
    rng = random.Random(20261007)
    cases = [[], [2, -1, 3], [0], [-3, -3], [1, 3, 7, 9], [1, 2, 2], [5, 5, 0, 0]]
    cases += [[rng.randint(-8, 10) for _ in range(n)] for n in range(1, 14)]
    return [
        dict(
            input=f"{len(a)}\n" + " ".join(map(str, a)) + "\n",
            expected=str(scope["oracle"](a)) + "\n",
            visibility="public" if i < 2 else "hidden",
        )
        for i, a in enumerate(cases)
    ]


def build_pack(runtime_refs: dict[str, str]) -> SkillPack:
    concepts = [
        dict(
            id=k,
            title=title,
            competency=f"Implement and explain {title.lower()}.",
            explanation=lesson,
            examples=[example],
            misconceptions=["Confusing an example with independent evidence"],
            evidence_modes=["recognize", "trace", "implement", "analyze", "retain"],
            estimated_minutes=30,
            accessibility="Plain text, keyboard accessible",
        )
        for k, title, _, lesson, example, *_ in CONCEPTS
    ]
    ids = [x[0] for x in CONCEPTS]
    tracks = [
        dict(id=t, goals=[t], concept_ids=ids, help_ceiling=3, maximum_daily_minutes=90)
        for t in ("foundations", "interview", "competitive")
    ]
    goals = [
        dict(
            id=t,
            title=t.title(),
            outcome="Demonstrate independent DSA capability with delayed retention evidence",
            track_id=t,
            required_fields=[
                "target_date",
                "days_per_week",
                "minutes_per_session",
                "timezone",
                "language",
            ],
            released_targets=targets(t),
        )
        for t in ("foundations", "interview", "competitive")
    ]
    exercises, repairs, hints = [], [], []
    for concept, family, title, statement, py, cpp, java in TASKS:
        for difficulty in (1, 2):
            key = f"practice_{concept}_{family}_{difficulty}"
            variants = [
                dict(
                    language=lang,
                    starter_code=source(lang, None),
                    reference_solution=source(lang, body),
                    interface="stdin: n followed by n integers; stdout: one integer and newline",
                    runtime_ref=runtime_refs[lang],
                    time_limit_ms=5000,
                    memory_limit_mb=256,
                )
                for lang, body in zip(LANGUAGES, (py, cpp, java), strict=True)
            ]
            exercises.append(
                dict(
                    id=key,
                    title=title + (" — extension" if difficulty == 2 else ""),
                    concept_ids=[concept],
                    inventory="practice",
                    modality="code",
                    evidence_mode="implement",
                    statement=statement
                    + "\nInput: n then n integers. Constraints: 0 ≤ n ≤ 30, -10 ≤ value ≤ 10. Output: one integer.",
                    rubric="Exact deterministic output on public and hidden cases; sample content only",
                    difficulty=difficulty,
                    calibration="reviewed",
                    estimated_minutes=3,
                    family_id=f"practice_{concept}_{family}",
                    variants=variants,
                    tests=task_tests(py),
                    provenance=PROVENANCE,
                    accessibility="Text statement, keyboard editor",
                )
            )
            for lang in LANGUAGES:
                for level, content in (
                    (
                        1,
                        "Which value must your result describe after each visited element? Try an empty input and a one-element input first.",
                    ),
                    (
                        2,
                        "Trace the sample by hand, recording your state after each step. Compare your state update with the requested operation; check boundary cases before changing the loop.",
                    ),
                    (
                        3,
                        "Separate reading input from solving it. Initialize the state for empty input, then perform one justified update per relevant element. Print only the final result.",
                    ),
                ):
                    hints.append(
                        dict(
                            exercise_id=key,
                            language=lang,
                            level=level,
                            message=content,
                            question="What does your current state represent, and which boundary case tests that claim?",
                        )
                    )
        siblings = [x for x in TASKS if x[0] == concept and x[1] != family]
        if siblings:
            repairs.append(
                dict(
                    exercise_id=f"practice_{concept}_{family}_1",
                    variant_id=f"practice_{concept}_{siblings[0][1]}_1",
                    structural_change="Different computation with the same data-structure invariant",
                    review_reference="Original demo repair mapping",
                    calibration="reviewed",
                )
            )
    lessons = [
        dict(
            id=f"{track}_{lang}_{k}",
            track=track,
            language=lang,
            concept_ids=[k],
            title=title,
            instruction=lesson,
            examples=[example],
            language_notes=language_note(lang),
            pattern_recognition="Identify the sequence, lookup, or traversal invariant before coding.",
            correctness="State the invariant, show each update preserves it, and check termination.",
            complexity="Count visits and extra stored values separately. Explain the bound for this task.",
            retrieval_check=dict(
                id="retrieval",
                prompt=rp + " Enter one integer.",
                response=dict(kind="trace", answer=ra),
            ),
            exit_check=dict(
                id="exit", prompt=ep + " Enter one integer.", response=dict(kind="trace", answer=ea)
            ),
            calibration="reviewed",
            accessibility="Plain text and keyboard accessible",
            source_reference="Original sample lesson; not reviewed for release",
        )
        for track in ("foundations", "interview", "competitive")
        for lang in LANGUAGES
        for k, title, _, lesson, example, rp, ra, ep, ea in CONCEPTS
    ]
    blueprints, diagnostics, forms = assessment_inventory(exercises)
    pack = SkillPack.model_validate(
        dict(
            key="socrat_demo",
            version="1.0.0",
            domain="data_structures_and_algorithms",
            title="Socrat original sample curriculum — demo only",
            purpose="launch",
            change_log="Development sample; not release approved",
            modalities=["text", "code"],
            languages=list(LANGUAGES),
            provenance=PROVENANCE,
            concepts=concepts,
            edges=[
                dict(
                    prerequisite=p,
                    concept=k,
                    minimum_mastery=0.75,
                    rationale="Requires the preceding traversal or representation skill",
                )
                for k, _, p, *_ in CONCEPTS
                if p
            ],
            goals=goals,
            tracks=tracks,
            exercises=exercises,
            blueprints=blueprints,
            mastery_policy=dict(minimum_independent=2, minimum_families=2, retention_days=7),
            diagnostics=diagnostics,
            session_content_version="1.0.0",
            learning_lessons=lessons,
            structural_repairs=repairs,
            competitive_penalty=dict(
                wrong_submit_seconds=60,
                calibration="reviewed",
                review_reference="Demo timing policy only",
            ),
            tutor_hints=hints,
            assessment_forms=forms,
        )
    )
    return pack


def language_note(language: str) -> str:
    return {
        "python": "Use a list for ordered values, int for integer arithmetic, and print only the required result. Python integers do not overflow.",
        "cpp": "Use vector<long long> and long long for totals. Keep index checks explicit; signed and unsigned sizes differ. Compile as GNU C++20.",
        "java": "Use long[] and long for totals. The entry class is Solution. Arrays are fixed-length; use ArrayDeque for queue or stack operations. Java 21.",
    }[language]


def targets(track: str) -> list[dict]:
    if track == "foundations":
        return [
            dict(outcome=x)
            for x in ("programming_readiness", "foundational_dsa", "interview_entry_readiness")
        ]
    if track == "interview":
        return [
            dict(outcome=o, role_level=r)
            for o in ("screen_readiness", "interview_loop_readiness", "topic_repair")
            for r in ("intern", "new_grad", "early_career", "experienced_hire")
        ]
    return [
        dict(outcome=o, value=v, platform_or_format=p)
        for o in ("rating_band", "division_readiness", "topic_repair", "contest_consistency")
        for p in ("codeforces", "atcoder", "codechef")
        for v in ("1200", "1400", "1600", "beginner")
    ]


def assessment_inventory(exercises):
    blueprints, diagnostics, forms = [], [], []
    roots = CONCEPTS[:2]
    for track in ("foundations", "interview", "competitive"):
        items = []
        for k, title, _, _, _, rp, ra, ep, ea in roots:
            additional = (
                (
                    ("Start at 1, add 2, then add 4. What value remains?", "7"),
                    ("Replace x=9 with x=2, then multiply x by 3. What is x?", "6"),
                    ("Integer input is 8. Print input minus 5. What is printed?", "3"),
                    (
                        "Which value is the additive identity: the value that leaves a sum unchanged?",
                        "0",
                    ),
                )
                if k == "language_foundations"
                else (
                    ("Visit [1, 0, 1, 1] once and count positive entries. What is the count?", "3"),
                    ("A loop visits [2, 3, 4] and adds each value. What is the final total?", "9"),
                    ("How many visits does a loop make over an empty sequence?", "0"),
                    (
                        "A loop visits four entries and increments a counter once per entry. Starting at 0, where does it finish?",
                        "4",
                    ),
                )
            )
            for i, (prompt, answer) in enumerate(((rp, ra), (ep, ea), *additional)):
                key = f"diagnostic_{track}_{k}_{i}"
                item = text_item(key, [k], title, prompt + " Choose the resulting value.")
                item["evidence_mode"] = ("trace", "analyze", "recognize")[i % 3]
                exercises.append(item)
                items.append(
                    dict(
                        exercise_id=key,
                        stage="no_code_trace_and_reasoning"
                        if i == 0
                        else "dsa_trace_and_reasoning",
                        languages=list(LANGUAGES),
                        response=dict(
                            kind="choice",
                            answer="correct",
                            choices=[
                                dict(id="correct", label=answer),
                                dict(id="other", label=str(int(answer) + 1)),
                            ],
                        ),
                    )
                )
            if track != "foundations":
                # Experienced placement includes actual implementation, in a
                # protected family never selected for ordinary practice.
                example = next(
                    x
                    for x in exercises
                    if x["inventory"] == "practice"
                    and x["concept_ids"] == [k]
                    and x["difficulty"] == 1
                )
                code = deepcopy(example)
                code.update(
                    id=f"diagnostic_{track}_{k}_code",
                    family_id=f"diagnostic_{track}_{k}_code",
                    inventory="assessment",
                    title=title + " implementation check",
                )
                exercises.append(code)
                items.append(
                    dict(
                        exercise_id=code["id"],
                        stage="implementation_diagnostic",
                        languages=list(LANGUAGES),
                        response=dict(kind="implementation"),
                    )
                )
        blueprint = f"diagnostic_{track}"
        blueprints.append(
            dict(
                id=blueprint,
                kind="diagnostic",
                exercise_ids=[x["exercise_id"] for x in items],
                concept_ids=[x[0] for x in roots],
                scoring="deterministic",
            )
        )
        diagnostics.append(
            dict(
                blueprint_id=blueprint,
                track=track,
                languages=list(LANGUAGES),
                scope="objective_readiness" if track == "foundations" else "full_placement",
                minimum_per_concept=6,
                maximum_items=12 if track == "foundations" else 14,
                maximum_seconds=900,
                uncertainty_margin=0.01,
                items=items,
            )
        )
        for kind in ("baseline", "weekly", "final", "retention"):
            key = f"assessment_{track}_{kind}"
            # Future forms use distinct families and changed representations; never shown by practice.
            prompt, answer = {
                "baseline": (
                    "A loop reads 6 then -2. Its accumulator starts at 0 and adds each value. What is printed?",
                    "4",
                ),
                "weekly": (
                    "A sensor counter starts at 1 and visits three records, adding 2 each time. What is its final value?",
                    "7",
                ),
                "final": (
                    "Three boxes contain 5 tokens each. Remove 4 tokens from the combined collection. How many remain?",
                    "11",
                ),
                "retention": (
                    "An accumulator starts at -1. The values 3 and 4 are added, in order. What is its final value?",
                    "6",
                ),
            }[kind]
            exercises.append(
                text_item(
                    key,
                    [x[0] for x in roots],
                    kind.title() + " independent check",
                    prompt + " Enter one integer.",
                )
            )
            blueprints.append(
                dict(
                    id=key,
                    kind=kind,
                    exercise_ids=[key],
                    concept_ids=[x[0] for x in roots],
                    scoring="deterministic",
                )
            )
            forms.append(
                dict(
                    blueprint_id=key,
                    track=track,
                    languages=list(LANGUAGES),
                    parallel_group=f"{track}_baseline_final"
                    if kind in {"baseline", "final"}
                    else key,
                    maximum_seconds=900,
                    pass_score=0.8,
                    review_reference="Original objective sample; not release reviewed",
                    retention_representation="recall" if kind == "retention" else None,
                    items=[
                        dict(
                            exercise_id=key,
                            response=dict(kind="trace", answer=answer),
                            unfamiliar_representation=kind == "weekly",
                        )
                    ],
                )
            )
    return blueprints, diagnostics, forms


def text_item(key, concepts, title, statement):
    return dict(
        id=key,
        title=title,
        concept_ids=concepts,
        inventory="assessment",
        modality="text",
        evidence_mode="trace",
        statement=statement,
        rubric="Exact integer answer",
        difficulty=1,
        calibration="reviewed",
        estimated_minutes=1,
        family_id=key,
        provenance=PROVENANCE,
        accessibility="Plain text and keyboard accessible",
    )


def validated_pack(runtime_refs: dict[str, str]) -> tuple[SkillPack, dict]:
    pack = build_pack(runtime_refs)
    audit = planning_audit(pack)
    if not audit["ready"]:
        raise ValueError(
            "Demo inventory failed the unchanged planner audit: "
            + str(
                [
                    (
                        x["track"],
                        x["language"],
                        x["inventory_gaps"],
                        [s for s in x["scenarios"] if not s["ready"]][:1],
                    )
                    for x in audit["cells"]
                    if not x["ready"]
                ]
            )
        )
    return pack, audit
