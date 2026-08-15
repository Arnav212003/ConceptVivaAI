"""Curated DSA question bank used by ConceptVivaAI.

Each UI topic intentionally contains 10 questions with a 3 Easy / 4 Medium /
3 Hard split so a 10-question mixed mock can always honor that distribution.
Runner metadata is server-only and is stripped from API responses.
"""

from __future__ import annotations

import copy
import random
from typing import Any


def _starter(function_name: str, params: str) -> str:
    return (
        "class Solution:\n"
        f"    def {function_name}(self, {params}):\n"
        "        # Write your code here\n"
        "        pass"
    )


def _q(
    qid: str,
    title: str,
    topic: str,
    difficulty: str,
    pattern: str,
    function_name: str,
    params: str,
    tests: list[dict[str, Any]],
    *,
    arg_types: list[str] | None = None,
    return_type: str = "raw",
    compare: str = "exact",
    mutate_index: int | None = None,
    source: str = "LeetCode / Curated",
) -> dict[str, Any]:
    return {
        "id": qid,
        "title": title,
        "topic": topic,
        "difficulty": difficulty,
        "pattern": pattern,
        "source": source,
        "starter_code": _starter(function_name, params),
        "runner": {
            "entry": "function",
            "function": function_name,
            "tests": tests,
            "arg_types": arg_types or [],
            "return_type": return_type,
            "compare": compare,
            "mutate_index": mutate_index,
        },
    }


# Test-case values below are deliberately small. They are hidden from the UI and
# are meant to catch logic errors, not to replace a full online judge.
DSA_QUESTION_BANK = [
    # ------------------------------------------------------------------ Arrays
    _q("arr_001", "Two Sum", "Arrays", "Easy", "Hash Map", "twoSum", "nums, target", [
        {"args": [[2, 7, 11, 15], 9], "expected": [0, 1]},
        {"args": [[3, 2, 4], 6], "expected": [1, 2]},
        {"args": [[3, 3], 6], "expected": [0, 1]},
    ]),
    _q("arr_002", "Best Time to Buy and Sell Stock", "Arrays", "Easy", "Greedy / Min Tracking", "maxProfit", "prices", [
        {"args": [[7, 1, 5, 3, 6, 4]], "expected": 5},
        {"args": [[7, 6, 4, 3, 1]], "expected": 0},
        {"args": [[2, 4, 1]], "expected": 2},
    ]),
    _q("arr_003", "Contains Duplicate", "Arrays", "Easy", "Hash Set", "containsDuplicate", "nums", [
        {"args": [[1, 2, 3, 1]], "expected": True},
        {"args": [[1, 2, 3, 4]], "expected": False},
        {"args": [[1, 1, 1, 3, 3, 4, 3, 2, 4, 2]], "expected": True},
    ]),
    _q("arr_004", "Product of Array Except Self", "Arrays", "Medium", "Prefix / Suffix Product", "productExceptSelf", "nums", [
        {"args": [[1, 2, 3, 4]], "expected": [24, 12, 8, 6]},
        {"args": [[-1, 1, 0, -3, 3]], "expected": [0, 0, 9, 0, 0]},
        {"args": [[2, 3]], "expected": [3, 2]},
    ]),
    _q("arr_005", "Maximum Subarray", "Arrays", "Medium", "Kadane's Algorithm", "maxSubArray", "nums", [
        {"args": [[-2, 1, -3, 4, -1, 2, 1, -5, 4]], "expected": 6},
        {"args": [[1]], "expected": 1},
        {"args": [[5, 4, -1, 7, 8]], "expected": 23},
    ]),
    _q("arr_006", "Subarray Sum Equals K", "Arrays", "Medium", "Prefix Sum + Hash Map", "subarraySum", "nums, k", [
        {"args": [[1, 1, 1], 2], "expected": 2},
        {"args": [[1, 2, 3], 3], "expected": 2},
        {"args": [[1, -1, 0], 0], "expected": 3},
    ]),
    _q("arr_007", "Rotate Array", "Arrays", "Medium", "Reversal / Cyclic Replacement", "rotate", "nums, k", [
        {"args": [[1, 2, 3, 4, 5, 6, 7], 3], "expected": [5, 6, 7, 1, 2, 3, 4]},
        {"args": [[-1, -100, 3, 99], 2], "expected": [3, 99, -1, -100]},
        {"args": [[1, 2], 5], "expected": [2, 1]},
    ], mutate_index=0),
    _q("arr_008", "Trapping Rain Water", "Arrays", "Hard", "Two Pointers / Prefix Max", "trap", "height", [
        {"args": [[0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]], "expected": 6},
        {"args": [[4, 2, 0, 3, 2, 5]], "expected": 9},
        {"args": [[1, 2, 3]], "expected": 0},
    ]),
    _q("arr_009", "First Missing Positive", "Arrays", "Hard", "Index Placement", "firstMissingPositive", "nums", [
        {"args": [[1, 2, 0]], "expected": 3},
        {"args": [[3, 4, -1, 1]], "expected": 2},
        {"args": [[7, 8, 9, 11, 12]], "expected": 1},
    ]),
    _q("arr_010", "Sliding Window Maximum", "Arrays", "Hard", "Monotonic Deque", "maxSlidingWindow", "nums, k", [
        {"args": [[1, 3, -1, -3, 5, 3, 6, 7], 3], "expected": [3, 3, 5, 5, 6, 7]},
        {"args": [[1], 1], "expected": [1]},
        {"args": [[9, 11], 2], "expected": [11]},
    ]),

    # ---------------------------------------------------------------- Strings
    _q("str_001", "Valid Palindrome", "Strings", "Easy", "Two Pointers", "isPalindrome", "s", [
        {"args": ["A man, a plan, a canal: Panama"], "expected": True},
        {"args": ["race a car"], "expected": False},
        {"args": [" "], "expected": True},
    ]),
    _q("str_002", "Valid Anagram", "Strings", "Easy", "Frequency Count", "isAnagram", "s, t", [
        {"args": ["anagram", "nagaram"], "expected": True},
        {"args": ["rat", "car"], "expected": False},
        {"args": ["aacc", "ccac"], "expected": False},
    ]),
    _q("str_003", "Longest Common Prefix", "Strings", "Easy", "Vertical Scan", "longestCommonPrefix", "strs", [
        {"args": [["flower", "flow", "flight"]], "expected": "fl"},
        {"args": [["dog", "racecar", "car"]], "expected": ""},
        {"args": [["interview", "internet", "internal"]], "expected": "inter"},
    ]),
    _q("str_004", "Longest Substring Without Repeating Characters", "Strings", "Medium", "Sliding Window", "lengthOfLongestSubstring", "s", [
        {"args": ["abcabcbb"], "expected": 3},
        {"args": ["bbbbb"], "expected": 1},
        {"args": ["pwwkew"], "expected": 3},
    ]),
    _q("str_005", "Group Anagrams", "Strings", "Medium", "Hash Map", "groupAnagrams", "strs", [
        {"args": [["eat", "tea", "tan", "ate", "nat", "bat"]], "expected": [["bat"], ["nat", "tan"], ["ate", "eat", "tea"]]},
        {"args": [[""]], "expected": [[""]]},
        {"args": [["a"]], "expected": [["a"]]},
    ], compare="unordered_nested"),
    _q("str_006", "Longest Palindromic Substring", "Strings", "Medium", "Expand Around Center", "longestPalindrome", "s", [
        {"args": ["babad"], "expected_any": ["bab", "aba"]},
        {"args": ["cbbd"], "expected": "bb"},
        {"args": ["a"], "expected": "a"},
    ], compare="any_of"),
    _q("str_007", "Decode String", "Strings", "Medium", "Stack", "decodeString", "s", [
        {"args": ["3[a]2[bc]"], "expected": "aaabcbc"},
        {"args": ["3[a2[c]]"], "expected": "accaccacc"},
        {"args": ["2[abc]3[cd]ef"], "expected": "abcabccdcdcdef"},
    ]),
    _q("str_008", "Minimum Window Substring", "Strings", "Hard", "Sliding Window", "minWindow", "s, t", [
        {"args": ["ADOBECODEBANC", "ABC"], "expected": "BANC"},
        {"args": ["a", "a"], "expected": "a"},
        {"args": ["a", "aa"], "expected": ""},
    ]),
    _q("str_009", "Regular Expression Matching", "Strings", "Hard", "Dynamic Programming", "isMatch", "s, p", [
        {"args": ["aa", "a"], "expected": False},
        {"args": ["aa", "a*"], "expected": True},
        {"args": ["ab", ".*"], "expected": True},
    ]),
    _q("str_010", "Palindrome Partitioning", "Strings", "Hard", "Backtracking", "partition", "s", [
        {"args": ["aab"], "expected": [["a", "a", "b"], ["aa", "b"]]},
        {"args": ["a"], "expected": [["a"]]},
        {"args": ["efe"], "expected": [["e", "f", "e"], ["efe"]]},
    ], compare="unordered_outer"),

    # ------------------------------------------------------------ Linked List
    _q("ll_001", "Reverse Linked List", "Linked List", "Easy", "Pointer Reversal", "reverseList", "head", [
        {"args": [[1, 2, 3, 4, 5]], "expected": [5, 4, 3, 2, 1]},
        {"args": [[1, 2]], "expected": [2, 1]},
        {"args": [[]], "expected": []},
    ], arg_types=["listnode"], return_type="listnode"),
    _q("ll_002", "Middle of the Linked List", "Linked List", "Easy", "Fast and Slow Pointers", "middleNode", "head", [
        {"args": [[1, 2, 3, 4, 5]], "expected": [3, 4, 5]},
        {"args": [[1, 2, 3, 4, 5, 6]], "expected": [4, 5, 6]},
        {"args": [[1]], "expected": [1]},
    ], arg_types=["listnode"], return_type="listnode"),
    _q("ll_003", "Merge Two Sorted Lists", "Linked List", "Easy", "Two Pointers", "mergeTwoLists", "list1, list2", [
        {"args": [[1, 2, 4], [1, 3, 4]], "expected": [1, 1, 2, 3, 4, 4]},
        {"args": [[], []], "expected": []},
        {"args": [[], [0]], "expected": [0]},
    ], arg_types=["listnode", "listnode"], return_type="listnode"),
    _q("ll_004", "Remove Nth Node From End", "Linked List", "Medium", "Two Pointers", "removeNthFromEnd", "head, n", [
        {"args": [[1, 2, 3, 4, 5], 2], "expected": [1, 2, 3, 5]},
        {"args": [[1], 1], "expected": []},
        {"args": [[1, 2], 1], "expected": [1]},
    ], arg_types=["listnode", "raw"], return_type="listnode"),
    _q("ll_005", "Add Two Numbers", "Linked List", "Medium", "Digit Simulation", "addTwoNumbers", "l1, l2", [
        {"args": [[2, 4, 3], [5, 6, 4]], "expected": [7, 0, 8]},
        {"args": [[0], [0]], "expected": [0]},
        {"args": [[9, 9, 9, 9, 9, 9, 9], [9, 9, 9, 9]], "expected": [8, 9, 9, 9, 0, 0, 0, 1]},
    ], arg_types=["listnode", "listnode"], return_type="listnode"),
    _q("ll_006", "Palindrome Linked List", "Linked List", "Medium", "Fast/Slow + Reverse", "isPalindrome", "head", [
        {"args": [[1, 2, 2, 1]], "expected": True},
        {"args": [[1, 2]], "expected": False},
        {"args": [[1]], "expected": True},
    ], arg_types=["listnode"]),
    _q("ll_007", "Partition List", "Linked List", "Medium", "Two Dummy Lists", "partition", "head, x", [
        {"args": [[1, 4, 3, 2, 5, 2], 3], "expected": [1, 2, 2, 4, 3, 5]},
        {"args": [[2, 1], 2], "expected": [1, 2]},
        {"args": [[], 0], "expected": []},
    ], arg_types=["listnode", "raw"], return_type="listnode"),
    _q("ll_008", "Reverse Nodes in k-Group", "Linked List", "Hard", "Pointer Manipulation", "reverseKGroup", "head, k", [
        {"args": [[1, 2, 3, 4, 5], 2], "expected": [2, 1, 4, 3, 5]},
        {"args": [[1, 2, 3, 4, 5], 3], "expected": [3, 2, 1, 4, 5]},
        {"args": [[1], 1], "expected": [1]},
    ], arg_types=["listnode", "raw"], return_type="listnode"),
    _q("ll_009", "Merge k Sorted Lists", "Linked List", "Hard", "Heap / Divide and Conquer", "mergeKLists", "lists", [
        {"args": [[[1, 4, 5], [1, 3, 4], [2, 6]]], "expected": [1, 1, 2, 3, 4, 4, 5, 6]},
        {"args": [[]], "expected": []},
        {"args": [[[]]], "expected": []},
    ], arg_types=["listnode_list"], return_type="listnode"),
    _q("ll_010", "Sort List", "Linked List", "Hard", "Merge Sort", "sortList", "head", [
        {"args": [[4, 2, 1, 3]], "expected": [1, 2, 3, 4]},
        {"args": [[-1, 5, 3, 4, 0]], "expected": [-1, 0, 3, 4, 5]},
        {"args": [[]], "expected": []},
    ], arg_types=["listnode"], return_type="listnode"),

    # ------------------------------------------------------------------ Stack
    _q("stk_001", "Valid Parentheses", "Stack", "Easy", "Stack", "isValid", "s", [
        {"args": ["()"], "expected": True},
        {"args": ["()[]{}"], "expected": True},
        {"args": ["(]"], "expected": False},
    ]),
    _q("stk_002", "Minimum Add to Make Parentheses Valid", "Stack", "Easy", "Balance Counter", "minAddToMakeValid", "s", [
        {"args": ["())"], "expected": 1},
        {"args": ["((("], "expected": 3},
        {"args": ["()"], "expected": 0},
    ]),
    _q("stk_003", "Next Greater Element I", "Stack", "Easy", "Monotonic Stack", "nextGreaterElement", "nums1, nums2", [
        {"args": [[4, 1, 2], [1, 3, 4, 2]], "expected": [-1, 3, -1]},
        {"args": [[2, 4], [1, 2, 3, 4]], "expected": [3, -1]},
        {"args": [[1], [1]], "expected": [-1]},
    ]),
    _q("stk_004", "Daily Temperatures", "Stack", "Medium", "Monotonic Stack", "dailyTemperatures", "temperatures", [
        {"args": [[73, 74, 75, 71, 69, 72, 76, 73]], "expected": [1, 1, 4, 2, 1, 1, 0, 0]},
        {"args": [[30, 40, 50, 60]], "expected": [1, 1, 1, 0]},
        {"args": [[30, 60, 90]], "expected": [1, 1, 0]},
    ]),
    _q("stk_005", "Asteroid Collision", "Stack", "Medium", "Stack Simulation", "asteroidCollision", "asteroids", [
        {"args": [[5, 10, -5]], "expected": [5, 10]},
        {"args": [[8, -8]], "expected": []},
        {"args": [[10, 2, -5]], "expected": [10]},
    ]),
    _q("stk_006", "Evaluate Reverse Polish Notation", "Stack", "Medium", "Stack Evaluation", "evalRPN", "tokens", [
        {"args": [["2", "1", "+", "3", "*"]], "expected": 9},
        {"args": [["4", "13", "5", "/", "+"]], "expected": 6},
        {"args": [["10", "6", "9", "3", "+", "-11", "*", "/", "*", "17", "+", "5", "+"]], "expected": 22},
    ]),
    _q("stk_007", "Simplify Path", "Stack", "Medium", "Stack", "simplifyPath", "path", [
        {"args": ["/home/"], "expected": "/home"},
        {"args": ["/../"], "expected": "/"},
        {"args": ["/home//foo/"], "expected": "/home/foo"},
    ]),
    _q("stk_008", "Largest Rectangle in Histogram", "Stack", "Hard", "Monotonic Stack", "largestRectangleArea", "heights", [
        {"args": [[2, 1, 5, 6, 2, 3]], "expected": 10},
        {"args": [[2, 4]], "expected": 4},
        {"args": [[1, 1]], "expected": 2},
    ]),
    _q("stk_009", "Maximal Rectangle", "Stack", "Hard", "Histogram + Monotonic Stack", "maximalRectangle", "matrix", [
        {"args": [[['1','0','1','0','0'],['1','0','1','1','1'],['1','1','1','1','1'],['1','0','0','1','0']]], "expected": 6},
        {"args": [[['0']]], "expected": 0},
        {"args": [[['1']]], "expected": 1},
    ]),
    _q("stk_010", "Basic Calculator", "Stack", "Hard", "Stack / Sign Simulation", "calculate", "s", [
        {"args": ["1 + 1"], "expected": 2},
        {"args": [" 2-1 + 2 "], "expected": 3},
        {"args": ["(1+(4+5+2)-3)+(6+8)"], "expected": 23},
    ]),

    # ------------------------------------------------------------------ Queue
    _q("que_001", "Generate Binary Numbers from 1 to N", "Queue", "Easy", "BFS Queue", "generateBinary", "n", [
        {"args": [5], "expected": ["1", "10", "11", "100", "101"]},
        {"args": [1], "expected": ["1"]},
        {"args": [3], "expected": ["1", "10", "11"]},
    ], source="GFG / Curated"),
    _q("que_002", "First Non-Repeating Character in a Stream", "Queue", "Easy", "Queue + Frequency", "firstNonRepeating", "stream", [
        {"args": ["aabc"], "expected": "a#bb"},
        {"args": ["zz"], "expected": "z#"},
        {"args": ["abc"], "expected": "aaa"},
    ], source="GFG / Curated"),
    _q("que_003", "Reverse First K Elements of Queue", "Queue", "Easy", "Queue + Stack", "reverseFirstK", "queue, k", [
        {"args": [[1, 2, 3, 4, 5], 3], "expected": [3, 2, 1, 4, 5]},
        {"args": [[1, 2, 3], 3], "expected": [3, 2, 1]},
        {"args": [[1], 1], "expected": [1]},
    ], source="GFG / Curated"),
    _q("que_004", "Sliding Window Average", "Queue", "Medium", "Sliding Window", "findAverages", "nums, k", [
        {"args": [[1, 2, 3, 4, 5], 3], "expected": [2.0, 3.0, 4.0]},
        {"args": [[5, 5], 1], "expected": [5.0, 5.0]},
        {"args": [[1, 3, 2, 6], 2], "expected": [2.0, 2.5, 4.0]},
    ], compare="approx_list", source="Curated"),
    _q("que_005", "First Negative Integer in Every Window", "Queue", "Medium", "Deque", "firstNegative", "nums, k", [
        {"args": [[-8, 2, 3, -6, 10], 2], "expected": [-8, 0, -6, -6]},
        {"args": [[1, 2, 3], 2], "expected": [0, 0]},
        {"args": [[-1, -2, -3], 1], "expected": [-1, -2, -3]},
    ], source="GFG / Curated"),
    _q("que_006", "Gas Station Circular Tour", "Queue", "Medium", "Greedy / Queue Concept", "canCompleteCircuit", "gas, cost", [
        {"args": [[1, 2, 3, 4, 5], [3, 4, 5, 1, 2]], "expected": 3},
        {"args": [[2, 3, 4], [3, 4, 3]], "expected": -1},
        {"args": [[5], [4]], "expected": 0},
    ]),
    _q("que_007", "Reveal Cards In Increasing Order", "Queue", "Medium", "Deque Simulation", "deckRevealedIncreasing", "deck", [
        {"args": [[17, 13, 11, 2, 3, 5, 7]], "expected": [2, 13, 3, 11, 5, 17, 7]},
        {"args": [[1, 1000]], "expected": [1, 1000]},
        {"args": [[3, 1, 2]], "expected": [1, 3, 2]},
    ]),
    _q("que_008", "Sliding Window Maximum", "Queue", "Hard", "Monotonic Deque", "maxSlidingWindow", "nums, k", [
        {"args": [[1, 3, -1, -3, 5, 3, 6, 7], 3], "expected": [3, 3, 5, 5, 6, 7]},
        {"args": [[1], 1], "expected": [1]},
        {"args": [[7, 2, 4], 2], "expected": [7, 4]},
    ]),
    _q("que_009", "Shortest Subarray with Sum at Least K", "Queue", "Hard", "Prefix Sum + Monotonic Deque", "shortestSubarray", "nums, k", [
        {"args": [[1], 1], "expected": 1},
        {"args": [[1, 2], 4], "expected": -1},
        {"args": [[2, -1, 2], 3], "expected": 3},
    ]),
    _q("que_010", "Constrained Subsequence Sum", "Queue", "Hard", "DP + Monotonic Deque", "constrainedSubsetSum", "nums, k", [
        {"args": [[10, 2, -10, 5, 20], 2], "expected": 37},
        {"args": [[-1, -2, -3], 1], "expected": -1},
        {"args": [[10, -2, -10, -5, 20], 2], "expected": 23},
    ]),

    # ---------------------------------------------------------- Binary Search
    _q("bs_001", "Binary Search", "Binary Search", "Easy", "Binary Search", "search", "nums, target", [
        {"args": [[-1, 0, 3, 5, 9, 12], 9], "expected": 4},
        {"args": [[-1, 0, 3, 5, 9, 12], 2], "expected": -1},
        {"args": [[5], 5], "expected": 0},
    ]),
    _q("bs_002", "Search Insert Position", "Binary Search", "Easy", "Lower Bound", "searchInsert", "nums, target", [
        {"args": [[1, 3, 5, 6], 5], "expected": 2},
        {"args": [[1, 3, 5, 6], 2], "expected": 1},
        {"args": [[1, 3, 5, 6], 7], "expected": 4},
    ]),
    _q("bs_003", "Sqrt(x)", "Binary Search", "Easy", "Binary Search on Answer", "mySqrt", "x", [
        {"args": [4], "expected": 2},
        {"args": [8], "expected": 2},
        {"args": [0], "expected": 0},
    ]),
    _q("bs_004", "Find First and Last Position", "Binary Search", "Medium", "Lower / Upper Bound", "searchRange", "nums, target", [
        {"args": [[5, 7, 7, 8, 8, 10], 8], "expected": [3, 4]},
        {"args": [[5, 7, 7, 8, 8, 10], 6], "expected": [-1, -1]},
        {"args": [[], 0], "expected": [-1, -1]},
    ]),
    _q("bs_005", "Search in Rotated Sorted Array", "Binary Search", "Medium", "Modified Binary Search", "search", "nums, target", [
        {"args": [[4, 5, 6, 7, 0, 1, 2], 0], "expected": 4},
        {"args": [[4, 5, 6, 7, 0, 1, 2], 3], "expected": -1},
        {"args": [[1], 0], "expected": -1},
    ]),
    _q("bs_006", "Find Minimum in Rotated Sorted Array", "Binary Search", "Medium", "Modified Binary Search", "findMin", "nums", [
        {"args": [[3, 4, 5, 1, 2]], "expected": 1},
        {"args": [[4, 5, 6, 7, 0, 1, 2]], "expected": 0},
        {"args": [[11, 13, 15, 17]], "expected": 11},
    ]),
    _q("bs_007", "Kth Missing Positive Number", "Binary Search", "Medium", "Binary Search on Missing Count", "findKthPositive", "arr, k", [
        {"args": [[2, 3, 4, 7, 11], 5], "expected": 9},
        {"args": [[1, 2, 3, 4], 2], "expected": 6},
        {"args": [[2], 1], "expected": 1},
    ]),
    _q("bs_008", "Median of Two Sorted Arrays", "Binary Search", "Hard", "Partition Binary Search", "findMedianSortedArrays", "nums1, nums2", [
        {"args": [[1, 3], [2]], "expected": 2.0},
        {"args": [[1, 2], [3, 4]], "expected": 2.5},
        {"args": [[], [1]], "expected": 1.0},
    ], compare="approx"),
    _q("bs_009", "Split Array Largest Sum", "Binary Search", "Hard", "Binary Search on Answer", "splitArray", "nums, k", [
        {"args": [[7, 2, 5, 10, 8], 2], "expected": 18},
        {"args": [[1, 2, 3, 4, 5], 2], "expected": 9},
        {"args": [[1, 4, 4], 3], "expected": 4},
    ]),
    _q("bs_010", "Aggressive Cows", "Binary Search", "Hard", "Binary Search on Answer", "aggressiveCows", "stalls, k", [
        {"args": [[1, 2, 4, 8, 9], 3], "expected": 3},
        {"args": [[10, 1, 2, 7, 5], 3], "expected": 4},
        {"args": [[1, 2], 2], "expected": 1},
    ], source="SPOJ / GFG / Curated"),

    # ------------------------------------------------------------------ Trees
    _q("tr_001", "Maximum Depth of Binary Tree", "Trees", "Easy", "DFS / BFS", "maxDepth", "root", [
        {"args": [[3, 9, 20, None, None, 15, 7]], "expected": 3},
        {"args": [[1, None, 2]], "expected": 2},
        {"args": [[]], "expected": 0},
    ], arg_types=["tree"]),
    _q("tr_002", "Same Tree", "Trees", "Easy", "DFS", "isSameTree", "p, q", [
        {"args": [[1, 2, 3], [1, 2, 3]], "expected": True},
        {"args": [[1, 2], [1, None, 2]], "expected": False},
        {"args": [[1, 2, 1], [1, 1, 2]], "expected": False},
    ], arg_types=["tree", "tree"]),
    _q("tr_003", "Invert Binary Tree", "Trees", "Easy", "DFS / BFS", "invertTree", "root", [
        {"args": [[4, 2, 7, 1, 3, 6, 9]], "expected": [4, 7, 2, 9, 6, 3, 1]},
        {"args": [[2, 1, 3]], "expected": [2, 3, 1]},
        {"args": [[]], "expected": []},
    ], arg_types=["tree"], return_type="tree"),
    _q("tr_004", "Binary Tree Level Order Traversal", "Trees", "Medium", "BFS", "levelOrder", "root", [
        {"args": [[3, 9, 20, None, None, 15, 7]], "expected": [[3], [9, 20], [15, 7]]},
        {"args": [[1]], "expected": [[1]]},
        {"args": [[]], "expected": []},
    ], arg_types=["tree"]),
    _q("tr_005", "Diameter of Binary Tree", "Trees", "Medium", "Postorder DFS", "diameterOfBinaryTree", "root", [
        {"args": [[1, 2, 3, 4, 5]], "expected": 3},
        {"args": [[1, 2]], "expected": 1},
        {"args": [[1]], "expected": 0},
    ], arg_types=["tree"]),
    _q("tr_006", "Validate Binary Search Tree", "Trees", "Medium", "Bounds / Inorder", "isValidBST", "root", [
        {"args": [[2, 1, 3]], "expected": True},
        {"args": [[5, 1, 4, None, None, 3, 6]], "expected": False},
        {"args": [[2, 2, 2]], "expected": False},
    ], arg_types=["tree"]),
    _q("tr_007", "Binary Tree Right Side View", "Trees", "Medium", "BFS / DFS", "rightSideView", "root", [
        {"args": [[1, 2, 3, None, 5, None, 4]], "expected": [1, 3, 4]},
        {"args": [[1, None, 3]], "expected": [1, 3]},
        {"args": [[]], "expected": []},
    ], arg_types=["tree"]),
    _q("tr_008", "Binary Tree Maximum Path Sum", "Trees", "Hard", "Postorder DP", "maxPathSum", "root", [
        {"args": [[1, 2, 3]], "expected": 6},
        {"args": [[-10, 9, 20, None, None, 15, 7]], "expected": 42},
        {"args": [[-3]], "expected": -3},
    ], arg_types=["tree"]),
    _q("tr_009", "Vertical Order Traversal of a Binary Tree", "Trees", "Hard", "DFS + Sorting", "verticalTraversal", "root", [
        {"args": [[3, 9, 20, None, None, 15, 7]], "expected": [[9], [3, 15], [20], [7]]},
        {"args": [[1, 2, 3, 4, 5, 6, 7]], "expected": [[4], [2], [1, 5, 6], [3], [7]]},
        {"args": [[1]], "expected": [[1]]},
    ], arg_types=["tree"]),
    _q("tr_010", "Recover Binary Search Tree", "Trees", "Hard", "Inorder Traversal", "recoverTree", "root", [
        {"args": [[1, 3, None, None, 2]], "expected": [3, 1, None, None, 2]},
        {"args": [[3, 1, 4, None, None, 2]], "expected": [2, 1, 4, None, None, 3]},
        {"args": [[2, 1, 3]], "expected": [2, 1, 3]},
    ], arg_types=["tree"], return_type="tree", mutate_index=0),

    # ----------------------------------------------------------------- Graphs
    _q("gr_001", "BFS Traversal of Graph", "Graphs", "Easy", "Breadth First Search", "bfsOfGraph", "V, adj", [
        {"args": [5, [[1, 2, 3], [0], [0, 4], [0], [2]]], "expected": [0, 1, 2, 3, 4]},
        {"args": [3, [[1], [0, 2], [1]]], "expected": [0, 1, 2]},
        {"args": [1, [[]]], "expected": [0]},
    ], source="GFG / Curated"),
    _q("gr_002", "DFS Traversal of Graph", "Graphs", "Easy", "Depth First Search", "dfsOfGraph", "V, adj", [
        {"args": [5, [[1, 2, 3], [0], [0, 4], [0], [2]]], "expected": [0, 1, 2, 4, 3]},
        {"args": [3, [[1], [0, 2], [1]]], "expected": [0, 1, 2]},
        {"args": [1, [[]]], "expected": [0]},
    ], source="GFG / Curated"),
    _q("gr_003", "Number of Islands", "Graphs", "Easy", "DFS / BFS", "numIslands", "grid", [
        {"args": [[['1','1','1','1','0'],['1','1','0','1','0'],['1','1','0','0','0'],['0','0','0','0','0']]], "expected": 1},
        {"args": [[['1','1','0','0','0'],['1','1','0','0','0'],['0','0','1','0','0'],['0','0','0','1','1']]], "expected": 3},
        {"args": [[['0']]], "expected": 0},
    ]),
    _q("gr_004", "Course Schedule", "Graphs", "Medium", "Topological Sort", "canFinish", "numCourses, prerequisites", [
        {"args": [2, [[1, 0]]], "expected": True},
        {"args": [2, [[1, 0], [0, 1]]], "expected": False},
        {"args": [1, []], "expected": True},
    ]),
    _q("gr_005", "Rotting Oranges", "Graphs", "Medium", "Multi-source BFS", "orangesRotting", "grid", [
        {"args": [[[2, 1, 1], [1, 1, 0], [0, 1, 1]]], "expected": 4},
        {"args": [[[2, 1, 1], [0, 1, 1], [1, 0, 1]]], "expected": -1},
        {"args": [[[0, 2]]], "expected": 0},
    ]),
    _q("gr_006", "Number of Provinces", "Graphs", "Medium", "DFS / Union Find", "findCircleNum", "isConnected", [
        {"args": [[[1, 1, 0], [1, 1, 0], [0, 0, 1]]], "expected": 2},
        {"args": [[[1, 0, 0], [0, 1, 0], [0, 0, 1]]], "expected": 3},
        {"args": [[[1]]], "expected": 1},
    ]),
    _q("gr_007", "Surrounded Regions", "Graphs", "Medium", "DFS / BFS from Border", "solve", "board", [
        {"args": [[['X','X','X','X'],['X','O','O','X'],['X','X','O','X'],['X','O','X','X']]], "expected": [['X','X','X','X'],['X','X','X','X'],['X','X','X','X'],['X','O','X','X']]},
        {"args": [[['X']]], "expected": [['X']]},
        {"args": [[['O']]], "expected": [['O']]},
    ], mutate_index=0),
    _q("gr_008", "Word Ladder", "Graphs", "Hard", "BFS", "ladderLength", "beginWord, endWord, wordList", [
        {"args": ["hit", "cog", ["hot", "dot", "dog", "lot", "log", "cog"]], "expected": 5},
        {"args": ["hit", "cog", ["hot", "dot", "dog", "lot", "log"]], "expected": 0},
        {"args": ["a", "c", ["a", "b", "c"]], "expected": 2},
    ]),
    _q("gr_009", "Network Delay Time", "Graphs", "Hard", "Dijkstra", "networkDelayTime", "times, n, k", [
        {"args": [[[2, 1, 1], [2, 3, 1], [3, 4, 1]], 4, 2], "expected": 2},
        {"args": [[[1, 2, 1]], 2, 1], "expected": 1},
        {"args": [[[1, 2, 1]], 2, 2], "expected": -1},
    ]),
    _q("gr_010", "Cheapest Flights Within K Stops", "Graphs", "Hard", "Bellman-Ford / Shortest Path", "findCheapestPrice", "n, flights, src, dst, k", [
        {"args": [4, [[0,1,100],[1,2,100],[2,0,100],[1,3,600],[2,3,200]], 0, 3, 1], "expected": 700},
        {"args": [3, [[0,1,100],[1,2,100],[0,2,500]], 0, 2, 1], "expected": 200},
        {"args": [3, [[0,1,100],[1,2,100],[0,2,500]], 0, 2, 0], "expected": 500},
    ]),

    # ------------------------------------------------------- Dynamic Programming
    _q("dp_001", "Climbing Stairs", "Dynamic Programming", "Easy", "1D DP", "climbStairs", "n", [
        {"args": [2], "expected": 2},
        {"args": [3], "expected": 3},
        {"args": [5], "expected": 8},
    ]),
    _q("dp_002", "House Robber", "Dynamic Programming", "Easy", "1D DP", "rob", "nums", [
        {"args": [[1, 2, 3, 1]], "expected": 4},
        {"args": [[2, 7, 9, 3, 1]], "expected": 12},
        {"args": [[2, 1, 1, 2]], "expected": 4},
    ]),
    _q("dp_003", "Min Cost Climbing Stairs", "Dynamic Programming", "Easy", "1D DP", "minCostClimbingStairs", "cost", [
        {"args": [[10, 15, 20]], "expected": 15},
        {"args": [[1, 100, 1, 1, 1, 100, 1, 1, 100, 1]], "expected": 6},
        {"args": [[0, 0]], "expected": 0},
    ]),
    _q("dp_004", "Coin Change", "Dynamic Programming", "Medium", "Unbounded Knapsack", "coinChange", "coins, amount", [
        {"args": [[1, 2, 5], 11], "expected": 3},
        {"args": [[2], 3], "expected": -1},
        {"args": [[1], 0], "expected": 0},
    ]),
    _q("dp_005", "Unique Paths", "Dynamic Programming", "Medium", "Grid DP", "uniquePaths", "m, n", [
        {"args": [3, 7], "expected": 28},
        {"args": [3, 2], "expected": 3},
        {"args": [1, 1], "expected": 1},
    ]),
    _q("dp_006", "Longest Increasing Subsequence", "Dynamic Programming", "Medium", "DP / Binary Search", "lengthOfLIS", "nums", [
        {"args": [[10, 9, 2, 5, 3, 7, 101, 18]], "expected": 4},
        {"args": [[0, 1, 0, 3, 2, 3]], "expected": 4},
        {"args": [[7, 7, 7, 7]], "expected": 1},
    ]),
    _q("dp_007", "Word Break", "Dynamic Programming", "Medium", "DP + Hash Set", "wordBreak", "s, wordDict", [
        {"args": ["leetcode", ["leet", "code"]], "expected": True},
        {"args": ["applepenapple", ["apple", "pen"]], "expected": True},
        {"args": ["catsandog", ["cats", "dog", "sand", "and", "cat"]], "expected": False},
    ]),
    _q("dp_008", "Edit Distance", "Dynamic Programming", "Hard", "2D DP", "minDistance", "word1, word2", [
        {"args": ["horse", "ros"], "expected": 3},
        {"args": ["intention", "execution"], "expected": 5},
        {"args": ["", "abc"], "expected": 3},
    ]),
    _q("dp_009", "Burst Balloons", "Dynamic Programming", "Hard", "Interval DP", "maxCoins", "nums", [
        {"args": [[3, 1, 5, 8]], "expected": 167},
        {"args": [[1, 5]], "expected": 10},
        {"args": [[1]], "expected": 1},
    ]),
    _q("dp_010", "Regular Expression Matching", "Dynamic Programming", "Hard", "2D DP", "isMatch", "s, p", [
        {"args": ["aa", "a"], "expected": False},
        {"args": ["aa", "a*"], "expected": True},
        {"args": ["aab", "c*a*b"], "expected": True},
    ]),
]


def _public_question(question: dict[str, Any]) -> dict[str, Any]:
    public = copy.deepcopy(question)
    public.pop("runner", None)
    return public


def get_all_dsa_questions():
    return [_public_question(q) for q in DSA_QUESTION_BANK]


def get_dsa_questions_by_difficulty(difficulty):
    difficulty = difficulty.lower().strip()
    return [_public_question(q) for q in DSA_QUESTION_BANK if q["difficulty"].lower() == difficulty]


def get_dsa_questions_by_topic(topic):
    topic = topic.lower().strip()
    return [_public_question(q) for q in DSA_QUESTION_BANK if q["topic"].lower() == topic]


def get_dsa_questions_by_topic_and_difficulty(topic, difficulty):
    topic = topic.lower().strip()
    difficulty = difficulty.lower().strip()
    return [
        _public_question(q)
        for q in DSA_QUESTION_BANK
        if q["topic"].lower() == topic and q["difficulty"].lower() == difficulty
    ]


def get_dsa_question_by_id(question_id):
    for question in DSA_QUESTION_BANK:
        if question["id"] == question_id:
            return question
    return None


def get_dsa_question_by_title(title):
    title = title.lower().strip()
    for question in DSA_QUESTION_BANK:
        if question["title"].lower().strip() == title:
            return question
    return None


def _topic_pool(topic: str) -> list[dict[str, Any]]:
    topic_key = topic.lower().strip()
    return [q for q in DSA_QUESTION_BANK if q["topic"].lower() == topic_key]


def get_dsa_mock_set(topic="Arrays", difficulty="Mixed", count=10):
    """Return a mock set.

    Mixed 10-question mocks are exactly 3 Easy + 4 Medium + 3 Hard. For other
    counts we use a near-even distribution while never duplicating a question.
    """
    pool = _topic_pool(topic)
    difficulty_key = difficulty.lower().strip()
    count = max(1, min(int(count or 10), 50))

    if difficulty_key != "mixed":
        selected_pool = [q for q in pool if q["difficulty"].lower() == difficulty_key]
        return [_public_question(q) for q in random.sample(selected_pool, min(count, len(selected_pool)))]

    buckets = {
        "easy": [q for q in pool if q["difficulty"].lower() == "easy"],
        "medium": [q for q in pool if q["difficulty"].lower() == "medium"],
        "hard": [q for q in pool if q["difficulty"].lower() == "hard"],
    }

    if count == 10 and all(len(buckets[name]) >= needed for name, needed in (("easy", 3), ("medium", 4), ("hard", 3))):
        selected = (
            random.sample(buckets["easy"], 3)
            + random.sample(buckets["medium"], 4)
            + random.sample(buckets["hard"], 3)
        )
        random.shuffle(selected)
        return [_public_question(q) for q in selected]

    # Generic balanced fallback for non-10 counts.
    targets = {"easy": count // 3, "medium": count // 3, "hard": count // 3}
    for name in ("medium", "easy", "hard")[: count % 3]:
        targets[name] += 1

    selected: list[dict[str, Any]] = []
    for name in ("easy", "medium", "hard"):
        take = min(targets[name], len(buckets[name]))
        selected.extend(random.sample(buckets[name], take))

    if len(selected) < count:
        remaining = [q for q in pool if q not in selected]
        selected.extend(random.sample(remaining, min(count - len(selected), len(remaining))))

    random.shuffle(selected)
    return [_public_question(q) for q in selected[:count]]


def get_dsa_practice_question(topic="Arrays", difficulty="Mixed"):
    pool = _topic_pool(topic)
    difficulty_key = difficulty.lower().strip()

    if difficulty_key != "mixed":
        pool = [q for q in pool if q["difficulty"].lower() == difficulty_key]

    if not pool:
        return None

    return random.choice(pool)
