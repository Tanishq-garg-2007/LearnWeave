export * from "./http";
export * from "./types";
export * as authApi from "./auth";
export * as roadmapsApi from "./roadmaps";
export * as goalsApi from "./goals";
export * as lessonsApi from "./lessons";
export * as quizApi from "./quiz";
export * as notesApi from "./notes";
export * as scheduleApi from "./schedule";
export * as communityApi from "./community";
export * as voiceApi from "./voice";
export * as cycleApi from "./cycle";
export * as profileApi from "./profile";
export * as healthApi from "./health";

import * as auth from "./auth";
import * as roadmaps from "./roadmaps";
import * as goals from "./goals";
import * as lessons from "./lessons";
import * as quiz from "./quiz";
import * as notes from "./notes";
import * as schedule from "./schedule";
import * as community from "./community";
import * as voice from "./voice";
import * as cycle from "./cycle";
import * as profile from "./profile";
import * as health from "./health";

export const api = {
  // Auth & Profile
  register: auth.register,
  login: auth.login,
  getMe: auth.getMe,
  updateProfile: profile.updateProfile,
  deleteAccount: profile.deleteAccount,

  // Goals & Roadmaps
  createGoalAndRoadmap: goals.createGoalAndRoadmap,
  listGoals: goals.listGoals,
  getGoalById: goals.getGoalById,
  getActiveRoadmap: roadmaps.getActiveRoadmap,
  getRoadmapById: roadmaps.getRoadmapById,
  getRoadmapVersions: roadmaps.getRoadmapVersions,
  updateLessonStatus: roadmaps.updateLessonStatus,

  // Notes & RAG Knowledge
  listNotes: notes.listNotes,
  uploadNote: notes.uploadNote,
  getNoteById: notes.getNoteById,
  deleteNote: notes.deleteNote,
  searchNotes: notes.searchNotes,

  // Lessons
  generateLesson: lessons.generateLesson,
  getLesson: lessons.getLesson,
  askDoubt: lessons.askDoubt,
  listLessonAttempts: lessons.listLessonAttempts,

  // Quiz & Evaluations
  generateQuiz: quiz.generateQuiz,
  getQuiz: quiz.getQuiz,
  submitQuiz: quiz.submitQuiz,

  // Learning Cycle State Machine
  startCycle: cycle.startCycle,
  getCycleState: cycle.getCycleState,
  submitCycleStep: cycle.submitCycleStep,

  // Voice Pipeline
  speak: voice.speak,
  listen: voice.listen,

  // Schedules
  getSchedule: schedule.getSchedule,
  generateSchedule: schedule.generateSchedule,
  completeScheduleSession: schedule.completeScheduleSession,

  // Community Library
  getCommunityNotes: community.getCommunityNotes,
  voteCommunityNote: community.voteCommunityNote,
  importCommunityNote: community.importCommunityNote,
  reportCommunityNote: community.reportCommunityNote,
  publishNote: community.publishNote,

  // Health Checks
  checkHealth: health.checkHealth,
  checkReadiness: health.checkReadiness,
};

export default api;
